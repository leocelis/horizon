"""FidelityMonitor — the public entry point for the Horizon Fidelity Monitor."""

from __future__ import annotations

import dataclasses
import logging
import uuid
from datetime import datetime
from typing import Any

_log = logging.getLogger(__name__)

# Events that exist in the evaluator but have NOT been through the V2 signal
# quality gate (300+ labelled turns per type, P≥0.7 / R≥0.7).  Activating them
# without domain-level validation is at the deployer's risk.  See LEGAL.md §3.3.
_UNGATED_EVENTS: frozenset[str] = frozenset(
    {"signal.grounding_required", "signal.pace_premature_report"}
)

import numpy as np

from horizon.config import Config
from horizon.context.window import update_context_window
from horizon.engines.coherence import compute_bipredictability
from horizon.engines.divergence import compute_divergence
from horizon.engines.embedding import EmbeddingEngine, update_history
from horizon.engines.epsilon import estimate_epsilon
from horizon.engines.fidelity import (
    compute_dynamic_fidelity,
    compute_health,
    compute_snapshot_fidelity,
)
from horizon.engines.igt import compute_igt, compute_igt_trend
from horizon.engines.mode import detect_conversation_mode
from horizon.engines.twr import compute_twr, split_sentences
from horizon.events.evaluator import evaluate_events
from horizon.grounding import (
    GroundingHookError,
    GroundingResult,
    ToolHook,
    call_hook,
    estimate_grounding_need,
)
from horizon.models import (
    ConfigResult,
    ConfigWarning,
    Event,
    ExportResult,
    FidelityTrajectory,
    TurnResult,
)
from horizon.session import Session, TurnState
from horizon.spacetime.circadian import compute_circadian_factor
from horizon.spacetime.deictic import resolve_deictic_expressions
from horizon.spacetime.interval import compute_spacetime_interval
from horizon.spacetime.light_cone import compute_reachability
from horizon.spacetime.pacing import detect_completion_marker, detect_deferred_action
from horizon.spacetime.spatial import compute_spatial_constraint, infer_location_class
from horizon.spacetime.temporal import (
    compute_resumption_cost,
    compute_retention,
    compute_temporal_asymmetry_penalty,
    compute_temporal_gap,
)
from horizon.spacetime.velocity import compute_acceleration, compute_velocity


class SessionNotFoundError(KeyError):
    """Raised when an operation references an unknown session_id."""


class FidelityMonitor:
    """Runtime fidelity monitor for multi-turn AI agent conversations.

    Stateless per-call, stateful per-session. Thread-safe for concurrent
    process_turn calls on different sessions; serialised on the same session.

    Usage::

        monitor = FidelityMonitor()
        session_id = monitor.new_conversation()
        result = monitor.process_turn(session_id, human_msg, agent_resp,
                                       timestamp="2026-04-22T10:30:00+00:00")
        print(result.fidelity_score, result.events)
    """

    def __init__(
        self,
        config: Config | None = None,
        store: Any | None = None,
        grounding_hook: ToolHook | None = None,
    ) -> None:
        """Initialise the monitor.

        Args:
            config: Global default config. Can be overridden per-session via configure().
            store: Optional PersistentDynamicsStore for cross-session persistence.
            grounding_hook: Optional callable (see horizon.grounding.ToolHook) invoked
                            when a turn looks ungrounded. With no hook, Horizon makes
                            zero outbound calls — privacy invariant preserved.
        """
        self._config = config or Config()
        self._sessions: dict[str, Session] = {}
        self._embed_engine = EmbeddingEngine(
            model_name=self._config.embedding_model,
            model_path=self._config.model_path,
        )
        self._store = store
        self._grounding_hook: ToolHook | None = grounding_hook
        self._last_grounding: dict[str, GroundingResult] = {}

    def preload_models(self) -> dict[str, float]:
        """Eagerly load and warm all on-disk models. Eliminates first-call latency.

        Production callers should invoke this at process startup so the first
        ``process_turn`` call is fast rather than blocking on the ~3-5s
        embedding-model load. Returns a small report with elapsed times per
        model so callers can budget cold-start windows.

        Safe to call repeatedly — already-loaded and already-warmed models are
        skipped.
        """
        import time

        report: dict[str, float] = {}
        t0 = time.perf_counter()
        was_loaded = self._embed_engine._model is not None
        self._embed_engine.ensure_loaded()
        if not was_loaded:
            # First load also pays a JIT/tokenizer warmup on the first encode.
            # Run a throwaway batch so the very next process_turn pays only the
            # core-pipeline cost.
            self._embed_engine.embed_batch(["warmup", "ready"])
        report["embedding_model_ms"] = (time.perf_counter() - t0) * 1000.0
        return report

    def register_grounding_hook(self, hook: ToolHook | None) -> None:
        """Attach (or detach with ``None``) an external grounding tool.

        Once registered, Horizon emits ``signal.grounding_required`` on
        turns where ungrounded specifics appear likely AND invokes the hook
        to fetch supporting evidence. Pass ``None`` to detach and restore
        the zero-outbound-call invariant.
        """
        self._grounding_hook = hook

    def get_last_grounding(self, session_id: str) -> GroundingResult | None:
        """Return the most recent GroundingResult for the session, if any."""
        return self._last_grounding.get(session_id)

    # ── Session lifecycle ───────────────────────────────────────────────────

    def new_conversation(
        self,
        metadata: dict | None = None,
        session_id: str | None = None,
    ) -> str:
        """Initialise a new conversation session and return its UUID.

        Args:
            metadata: Optional dict with domain, user_id, agent_name, config overrides.
            session_id: Optional explicit session ID (auto-generated UUID if omitted).
        """
        sid = session_id or str(uuid.uuid4())
        config = self._config

        if metadata:
            valid_fields = {f.name for f in dataclasses.fields(Config)}
            overrides = {k: v for k, v in metadata.items() if k in valid_fields}
            if overrides:
                config = config.merge(**overrides)

        session = Session(session_id=sid, config=config)

        if metadata and "max_context_tokens" in metadata:
            session.max_context_tokens = int(metadata["max_context_tokens"])

        self._sessions[sid] = session

        # Persist session record if store is configured
        if self._store:
            self._store.save_session(
                session_id=sid,
                user_id=metadata.get("user_id") if metadata else None,
                agent_name=metadata.get("agent_name") if metadata else None,
                domain=config.domain,
                metadata=metadata,
            )

        return sid

    def process_turn(
        self,
        session_id: str,
        human_message: str,
        agent_response: str,
        timestamp: str | None = None,
        client_context: dict | None = None,
        logprobs: list | None = None,
        human_latency_ms: float | None = None,
    ) -> TurnResult:
        """Process one conversation turn and return full fidelity metrics.

        Args:
            session_id: Session returned by new_conversation().
            human_message: The human's message text.
            agent_response: The agent's response text.
            timestamp: ISO 8601 wall-clock time of the human's message.
                       Enables all temporal, circadian, velocity, and spacetime signals.
            client_context: Optional dict with device_type, timezone, location_class,
                            ip_address, geoip_db_path. Enables spatial signals.
            logprobs: Optional token log probabilities (AI uncertainty channel, future).
            human_latency_ms: ms between agent response and human reply (ambient signal).

        Returns:
            TurnResult with all computed signals, fidelity score, and fired events.

        Raises:
            SessionNotFoundError: If session_id has not been registered.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(
                f"Session '{session_id}' not found. Call new_conversation() first."
            )

        session = self._sessions[session_id]

        with session._lock:
            return self._run_pipeline(
                session,
                human_message,
                agent_response,
                timestamp,
                client_context,
                logprobs,
                human_latency_ms,
            )

    def _run_pipeline(
        self,
        session: Session,
        human_message: str,
        agent_response: str,
        timestamp: str | None,
        client_context: dict | None,
        logprobs: list | None,
        human_latency_ms: float | None,
    ) -> TurnResult:
        """Full process_turn pipeline (called with session lock held)."""
        config = session.config
        turn_number = session.turn_count + 1

        # ── Step 1: Embed (one batched forward pass per turn) ─────────────
        agent_sentences = split_sentences(agent_response)
        embed_texts = [human_message, agent_response, *agent_sentences]
        turn_embeddings = self._embed_engine.embed_batch(embed_texts)
        h_emb, a_emb = turn_embeddings[0], turn_embeddings[1]
        agent_sentence_embeddings = turn_embeddings[2:]
        c_emb = (h_emb + a_emb) / 2.0
        norm = np.linalg.norm(c_emb)
        if norm > 1e-8:
            c_emb /= norm

        # ── Step 2: Core signals ──────────────────────────────────────────
        igt = compute_igt(c_emb, session.history_embedding, turn_number)
        igt_trend = compute_igt_trend(session, config.convergence_window)
        djs = compute_divergence(h_emb, a_emb)
        twr_sentence_out: list = []
        twr = compute_twr(
            agent_response,
            session,
            self._embed_engine.embed,
            sentence_embeddings=agent_sentence_embeddings or None,
            sentence_embeddings_out=twr_sentence_out,
        )
        agent_sentence_embeddings = twr_sentence_out
        consistency = compute_bipredictability(h_emb, a_emb, session.history_embedding)
        epsilon = estimate_epsilon(session, c_emb, djs)

        # ── Step 3: Temporal signals ──────────────────────────────────────
        gap_seconds: float | None = None
        gap_class = None
        retention: float | None = None
        delta_tau_penalty: float = 0.0
        kappa: float = 1.0
        circadian: float | None = None
        temporal_refs = None
        resumption = None
        ts_epoch: float | None = None

        if timestamp:
            ts_epoch = datetime.fromisoformat(timestamp).timestamp()
            prev_ts = session.turns[-1].timestamp if session.turns else None
            gap_seconds, gap_class = compute_temporal_gap(timestamp, prev_ts)

            tz_str = client_context.get("timezone") if client_context else None
            kappa = compute_circadian_factor(timestamp, tz_str, config.chronotype_offset)
            circadian = kappa

            retention = compute_retention(gap_seconds, config.context_half_life_hours, kappa)
            delta_tau_penalty = compute_temporal_asymmetry_penalty(
                gap_seconds, config.context_half_life_hours, kappa
            )
            resumption = compute_resumption_cost(gap_seconds, retention)
            temporal_refs = resolve_deictic_expressions(human_message, timestamp)

        # ── Step 4: Fidelity dynamics ─────────────────────────────────────
        evicted = update_context_window(session, human_message, agent_response)
        delta_recoverable = max(0.0, twr - 0.3)
        # Only count evictions above the minimum threshold to avoid classifying
        # routine single-token context trims as irreversible degradation
        # (which would fire signal.session_reset far too aggressively).
        delta_irreversible = max(0.0, (evicted - config.min_eviction_threshold) * 0.1)

        prev_fidelity = session.fidelity_trajectory[-1] if session.fidelity_trajectory else 0.5
        fidelity = compute_dynamic_fidelity(
            prev_fidelity,
            igt,
            djs,
            delta_recoverable,
            delta_irreversible,
            delta_tau_penalty,
            kappa,
            config,
            consistency=consistency,
        )

        # Turn 1: bootstrap fidelity from snapshot
        if turn_number == 1:
            fidelity = compute_snapshot_fidelity(igt, djs, twr, consistency, config)

        # ── Step 5: Health ────────────────────────────────────────────────
        session.fidelity_trajectory.append(fidelity)
        health = compute_health(session, fidelity, igt_trend, config, current_igt=igt)

        degradation: str = "none"
        if delta_irreversible > 0 and delta_recoverable > 0.1:
            degradation = "both"
        elif delta_irreversible > 0:
            degradation = "irreversible_loss"
        elif delta_recoverable > 0.1:
            degradation = "recoverable_drift"

        # ── Step 6: Pace ──────────────────────────────────────────────────
        velocity: float | None = None
        acceleration: float | None = None
        if timestamp and session.turns and gap_seconds and gap_seconds > 0:
            velocity = compute_velocity(c_emb, session.turns[-1].combined_embedding, gap_seconds)
            prev_vel = session.turns[-1].velocity
            acceleration = compute_acceleration(velocity, prev_vel)

        # ── Step 7: Spacetime interval ────────────────────────────────────
        ds2: float | None = None
        interval_class = None
        if timestamp and session.turns and gap_seconds:
            prev_turn = session.turns[-1]
            d_djs = abs(djs - prev_turn.divergence_score)
            d_eps = abs(epsilon - prev_turn.epsilon_t)
            d_coh = abs(consistency - prev_turn.consistency_score)
            ds2, interval_class = compute_spacetime_interval(
                gap_seconds, d_djs, d_eps, d_coh, config
            )

        # ── Step 8: Causal reachability ───────────────────────────────────
        # Reachability models the intersection of temporal decay, context
        # eviction, and semantic dissimilarity. Without a timestamp we cannot
        # compute the temporal-decay term, so we treat the whole signal as
        # opt-in (matches horizon_intent.yaml::temporal_signals_optional).
        reachable_count: int | None
        reachable_frac: float | None
        if timestamp is not None:
            reachable_count, reachable_frac = compute_reachability(
                session, turn_number, c_emb, gap_seconds or 0.0, kappa, config
            )
        else:
            reachable_count, reachable_frac = None, None

        # ── Step 9: Spatial ───────────────────────────────────────────────
        loc_class: str | None = None
        spatial = None
        spatial_shift: float | None = None
        if client_context:
            loc_class = infer_location_class(client_context)
            spatial = compute_spatial_constraint(client_context)
            if session.turns and session.turns[-1].client_context:
                prev_spatial = compute_spatial_constraint(session.turns[-1].client_context)
                spatial_shift = 0.0 if spatial == prev_spatial else 1.0

        # ── Step 10: Mode detection ───────────────────────────────────────
        mode = config.conversation_mode
        if mode == "auto":
            mode = detect_conversation_mode(session, h_emb, turn_number)
        session.detected_mode = mode

        # ── Step 11: Build TurnState and append ───────────────────────────
        # Pacing hints — computed from text now, consumed by next turn's
        # evaluator. Storing only the parsed flag/dataclass (never raw text)
        # preserves the privacy invariant.
        agent_pacing_hint = detect_deferred_action(agent_response)
        human_completion = detect_completion_marker(human_message)

        turn_state = TurnState(
            turn_number=turn_number,
            human_embedding=h_emb,
            agent_embedding=a_emb,
            combined_embedding=c_emb,
            agent_sentence_embeddings=agent_sentence_embeddings or None,
            timestamp=timestamp,
            timestamp_epoch=ts_epoch,
            client_context=client_context,
            igt_value=igt,
            divergence_score=djs,
            twr_value=twr,
            consistency_score=consistency,
            fidelity_score=fidelity,
            epsilon_t=epsilon,
            velocity=velocity,
            in_context=True,
            agent_pacing_hint=agent_pacing_hint,
            human_completion_marker=human_completion,
        )
        session.turns.append(turn_state)
        update_history(session, c_emb)

        # ── Step 11b: Grounding-need estimate + optional hook callout ─────
        # Always computed. The hook is only invoked when (a) a hook is
        # registered AND (b) the heuristic crosses the configured threshold
        # — preserves the privacy invariant for non-grounded deployments.
        grounding_need = estimate_grounding_need(human_message, agent_response, djs, consistency)
        grounding_evidence: list[str] = []
        grounding_sources: list[str] = []
        grounding_confidence: float = 0.0
        if (
            self._grounding_hook is not None
            and grounding_need >= config.grounding_required_threshold
        ):
            try:
                gres = call_hook(
                    self._grounding_hook,
                    human_message=human_message,
                    agent_draft=agent_response,
                )
                self._last_grounding[session.session_id] = gres
                if gres.grounded:
                    grounding_evidence = list(gres.evidence)
                    grounding_sources = list(gres.sources)
                    grounding_confidence = gres.confidence
            except GroundingHookError:
                # Don't crash the pipeline — caller can poll get_last_grounding()
                # to see why. Pipeline keeps the heuristic-only signal.
                pass

        # ── Step 12: Preliminary result for event engine ──────────────────
        preliminary = TurnResult(
            turn_number=turn_number,
            igt_value=igt,
            igt_trend=igt_trend,
            divergence_score=djs,
            twr_value=twr,
            consistency_score=consistency,
            fidelity_score=fidelity,
            health_status=health,
            degradation_type=degradation,
            events=[],
            epsilon_t=epsilon,
            conversation_mode=mode,
            gap_seconds=gap_seconds,
            gap_class=gap_class,
            estimated_retention=retention,
            temporal_asymmetry=delta_tau_penalty if timestamp else None,
            resumption_cost=resumption,
            circadian_factor=circadian,
            temporal_references=temporal_refs,
            conversation_velocity=velocity,
            conversation_acceleration=acceleration,
            spacetime_interval=ds2,
            interval_class=interval_class,
            reachable_turns=reachable_count,
            reachable_fraction=reachable_frac,
            location_class=loc_class,
            spatial_constraint=spatial,
            spatial_frame_shift=spatial_shift,
            grounding_need=grounding_need,
            grounding_evidence=grounding_evidence,
            grounding_sources=grounding_sources,
            grounding_confidence=grounding_confidence,
        )

        # ── Step 13: Events ───────────────────────────────────────────────
        events = evaluate_events(
            session,
            turn_state,
            preliminary,
            config,
            agent_response=agent_response,
        )
        session.event_log.extend(events)

        # Persist turn if store is configured
        if self._store:
            self._store.record_turn(
                session_id=session.session_id,
                turn_number=turn_number,
                timestamp=timestamp,
                fidelity_score=fidelity,
                igt_value=igt,
                divergence_score=djs,
                twr_value=twr,
                consistency_score=consistency,
                epsilon_t=epsilon,
                health_status=health,
                events=[dataclasses.asdict(e) for e in events],
            )

        return dataclasses.replace(preliminary, events=events)

    # ── Trajectory and events ───────────────────────────────────────────────

    def get_trajectory(self, session_id: str) -> FidelityTrajectory:
        """Return the full fidelity trajectory for a session."""
        session = self._get_session(session_id)

        scores = list(session.fidelity_trajectory)
        timestamps = [t.timestamp for t in session.turns]
        gaps: list[float | None] = [None]
        for i in range(1, len(session.turns)):
            ts_curr = session.turns[i].timestamp
            ts_prev = session.turns[i - 1].timestamp
            if ts_curr and ts_prev:
                from horizon.spacetime.temporal import compute_temporal_gap

                gap, _ = compute_temporal_gap(ts_curr, ts_prev)
                gaps.append(gap)
            else:
                gaps.append(None)

        # IGT trend over full trajectory
        if len(session.turns) >= 2:
            igt_values = [t.igt_value for t in session.turns]
            import numpy as np

            x = np.arange(len(igt_values), dtype=float)
            igt_trend = float(np.polyfit(x, igt_values, 1)[0])
        else:
            igt_trend = 0.0

        # T* estimate
        t_star: int | None = None
        if len(session.turns) >= 5 and igt_trend < 0:
            t_star = max(5, int(len(session.turns) / max(0.01, -igt_trend)))

        health = compute_health(session, scores[-1] if scores else 0.5, igt_trend, session.config)

        return FidelityTrajectory(
            session_id=session_id,
            turn_count=len(scores),
            scores=scores,
            timestamps=timestamps,
            gap_durations=gaps,
            igt_trend=igt_trend,
            health_status=health,
            estimated_t_star=t_star,
            peak_fidelity=max(scores) if scores else 0.0,
            current_fidelity=scores[-1] if scores else 0.0,
        )

    def get_events(self, session_id: str, active_only: bool = False) -> list[Event]:
        """Return all events fired in the session, optionally filtered to active-only."""
        session = self._get_session(session_id)
        if active_only:
            return [e for e in session.event_log if e.active]
        return list(session.event_log)

    # ── Configuration ───────────────────────────────────────────────────────

    def configure(
        self,
        session_id: str | None = None,
        **kwargs: object,
    ) -> ConfigResult:
        """Override config parameters for a session or globally.

        Supported kwargs match the Config dataclass fields. The intent also
        exposes three compound parameters that are flattened into individual
        Config fields (per HORIZON_TECH_SPEC.md §2.1):

            fidelity_weights={alpha, lambda_r, lambda_i, beta}
            temporal_weights={gamma, delta}
            spacetime_coefficients={alpha, beta, gamma, delta_st}
                → spacetime_alpha, spacetime_beta, spacetime_gamma, spacetime_delta

        The `embedding_model` parameter accepts the logical intent values
        (`local-sentence-transformer`, `openai-text-embedding-3-small`,
        `custom`) and resolves them to concrete identifiers.

        Returns ConfigResult with applied values and any validation warnings.
        """
        warnings: list[ConfigWarning] = []
        applied: dict = {}
        valid_fields = {f.name for f in dataclasses.fields(Config)}

        kwargs = self._flatten_configure_kwargs(kwargs, warnings)
        kwargs = self._resolve_embedding_model(kwargs, warnings)

        filtered = {}
        for k, v in kwargs.items():
            if k not in valid_fields:
                warnings.append(ConfigWarning(k, f"Unknown parameter '{k}' — ignored"))
            else:
                filtered[k] = v
                applied[k] = v

        # Warn when ungated event types are being set to active mode.
        # These events have not completed the V2 precision/recall validation gate
        # (300+ labelled turns, P≥0.7 / R≥0.7) and may fire incorrectly in
        # production deployments.  See LEGAL.md §3.3 and TERMS_OF_SERVICE.md §4.
        if "event_modes" in filtered:
            for event_type, mode in (filtered["event_modes"] or {}).items():
                if mode == "active" and event_type in _UNGATED_EVENTS:
                    msg = (
                        f"Activating '{event_type}' without V2 validation gate clearance. "
                        "This event has not been validated to P≥0.7/R≥0.7 on a labelled "
                        "corpus. Validate on your specific domain before production use. "
                        "See LEGAL.md §3.3."
                    )
                    _log.warning(msg)
                    warnings.append(ConfigWarning(event_type, msg))

        # Validate timezone if present in event_modes via temporal params
        if "temporal_desync_threshold_seconds" in filtered:
            val = filtered["temporal_desync_threshold_seconds"]
            if not isinstance(val, (int, float)) or val < 0:
                warnings.append(
                    ConfigWarning("temporal_desync_threshold_seconds", "Must be non-negative float")
                )
                del filtered["temporal_desync_threshold_seconds"]

        if session_id:
            session = self._get_session(session_id)
            session.config = session.config.merge(**filtered)
        else:
            self._config = self._config.merge(**filtered)
            # propagate to existing sessions
            for s in self._sessions.values():
                s.config = s.config.merge(**filtered)

        return ConfigResult(applied=applied, warnings=warnings)

    # ── Export ──────────────────────────────────────────────────────────────

    def export_to(
        self,
        session_id: str,
        target: str = "json",
        connection: Any | None = None,
    ) -> ExportResult:
        """Export session data to the specified target.

        Supported targets: 'json', 'langsmith', 'langfuse', 'otel', 'arize'.
        """
        from horizon.integrations.export import export_session

        session = self._get_session(session_id)
        return export_session(session, target, connection)

    # ── Wrap helpers (for SDK integration) ──────────────────────────────────

    def wrap(self, client: Any, session_id: str) -> Any:
        """Wrap an OpenAI or Anthropic client to auto-call process_turn after each response."""
        client_module = type(client).__module__

        if "openai" in client_module:
            from horizon.integrations.openai import HorizonWrappedOpenAI

            return HorizonWrappedOpenAI(client, self, session_id)
        if "anthropic" in client_module:
            from horizon.integrations.anthropic import HorizonWrappedAnthropic

            return HorizonWrappedAnthropic(client, self, session_id)

        raise TypeError(
            f"Cannot wrap client of type '{type(client).__name__}'. "
            "Supported: openai.OpenAI, anthropic.Anthropic"
        )

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        return self._sessions[session_id]

    @staticmethod
    def _flatten_configure_kwargs(
        kwargs: dict,
        warnings: list[ConfigWarning],
    ) -> dict:
        """Expand intent-level compound parameters to flat Config fields.

        Per HORIZON_TECH_SPEC.md §2.1, the intent's configure() accepts three
        compound parameters that map onto individual Config fields.
        """
        flat = dict(kwargs)

        fidelity_weights = flat.pop("fidelity_weights", None)
        if isinstance(fidelity_weights, dict):
            for key in ("alpha", "lambda_r", "lambda_i", "beta"):
                if key in fidelity_weights:
                    flat[key] = fidelity_weights[key]
        elif fidelity_weights is not None:
            warnings.append(
                ConfigWarning(
                    "fidelity_weights",
                    "Must be a dict with keys among {alpha, lambda_r, lambda_i, beta}",
                )
            )

        temporal_weights = flat.pop("temporal_weights", None)
        if isinstance(temporal_weights, dict):
            for key in ("gamma", "delta"):
                if key in temporal_weights:
                    flat[key] = temporal_weights[key]
        elif temporal_weights is not None:
            warnings.append(
                ConfigWarning(
                    "temporal_weights",
                    "Must be a dict with keys among {gamma, delta}",
                )
            )

        spacetime_coefficients = flat.pop("spacetime_coefficients", None)
        if isinstance(spacetime_coefficients, dict):
            st_map = {
                "alpha": "spacetime_alpha",
                "beta": "spacetime_beta",
                "gamma": "spacetime_gamma",
                "delta_st": "spacetime_delta",
                "delta": "spacetime_delta",
            }
            for src_key, dst_field in st_map.items():
                if src_key in spacetime_coefficients:
                    flat[dst_field] = spacetime_coefficients[src_key]
        elif spacetime_coefficients is not None:
            warnings.append(
                ConfigWarning(
                    "spacetime_coefficients",
                    "Must be a dict with keys among {alpha, beta, gamma, delta_st}",
                )
            )

        return flat

    @staticmethod
    def _resolve_embedding_model(
        kwargs: dict,
        warnings: list[ConfigWarning],
    ) -> dict:
        """Resolve intent's logical embedding_model values to concrete identifiers.

        Accepted logical values (from horizon_intent.yaml::configure.embedding_model):
            - "local-sentence-transformer" → "all-MiniLM-L6-v2"
            - "openai-text-embedding-3-small" → "text-embedding-3-small"
            - "custom" → caller must also pass model_path

        Concrete model slugs pass through unchanged.
        """
        resolved = dict(kwargs)
        logical = resolved.get("embedding_model")
        if not isinstance(logical, str):
            return resolved

        aliases = {
            "local-sentence-transformer": "all-MiniLM-L6-v2",
            "openai-text-embedding-3-small": "text-embedding-3-small",
        }
        if logical in aliases:
            resolved["embedding_model"] = aliases[logical]
        elif logical == "custom" and "model_path" not in resolved:
            warnings.append(
                ConfigWarning(
                    "embedding_model",
                    "embedding_model='custom' requires model_path to be set",
                )
            )
        return resolved
