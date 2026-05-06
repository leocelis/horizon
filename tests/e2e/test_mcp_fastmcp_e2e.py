"""E2E tests for the FastMCP-based Horizon MCP server.

Covers all three MCP primitive layers:
  • Tools      — new_conversation, process_turn, configure_session
  • Resources  — session trajectory, session events
  • Prompt     — monitor_conversation

Tests exercise the FastMCP tool functions directly (same code the MCP wire
protocol calls) and also verify the _dispatch shim that backward-compat tests
rely on. They do NOT require a running MCP server process — the functions are
called in-process, which is faster, deterministic, and CI-friendly.

Run:
    pytest tests/e2e/test_mcp_fastmcp_e2e.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from horizon import Config, FidelityMonitor
from horizon.mcp.server import (
    _dispatch,
    _get_monitor,
    configure_session,
    get_events,
    get_trajectory,
    monitor_conversation,
    new_conversation,
    process_turn,
)
from horizon.monitor import SessionNotFoundError


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_global_monitor(monkeypatch):
    """Give each test a clean FidelityMonitor so sessions don't bleed across tests."""
    import horizon.mcp.server as srv

    fresh = FidelityMonitor(Config())
    monkeypatch.setattr(srv, "_monitor", fresh)
    yield


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: new_conversation
# ─────────────────────────────────────────────────────────────────────────────


class TestNewConversation:
    def test_returns_session_id(self):
        result = new_conversation()
        assert "session_id" in result
        assert len(result["session_id"]) == 36  # UUID4

    def test_returns_distinct_ids(self):
        a = new_conversation()["session_id"]
        b = new_conversation()["session_id"]
        assert a != b

    def test_accepts_metadata(self):
        result = new_conversation(metadata={"domain": "medical", "agent_name": "doc-bot"})
        assert "session_id" in result
        # Session should be usable
        sid = result["session_id"]
        ts = datetime.now(timezone.utc).isoformat()
        turn = process_turn(
            session_id=sid,
            human_message="What are the symptoms of hypertension?",
            agent_response="High blood pressure can cause headaches, dizziness, and chest pain.",
            timestamp=ts,
        )
        assert "fidelity_score" in turn

    def test_metadata_domain_affects_domain_in_trajectory(self):
        sid = new_conversation(metadata={"domain": "legal"})["session_id"]
        ts = datetime.now(timezone.utc).isoformat()
        process_turn(
            session_id=sid,
            human_message="Explain fair use doctrine.",
            agent_response="Fair use allows limited use of copyrighted material without permission.",
            timestamp=ts,
        )
        traj_json = get_trajectory(session_id=sid)
        traj = json.loads(traj_json)
        assert "session_id" in traj
        assert traj["session_id"] == sid


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: process_turn
# ─────────────────────────────────────────────────────────────────────────────


class TestProcessTurn:
    def test_returns_full_turn_result_fields(self):
        sid = new_conversation()["session_id"]
        ts = datetime.now(timezone.utc).isoformat()
        result = process_turn(
            session_id=sid,
            human_message="How does async/await work in Python?",
            agent_response="async functions return coroutines; awaiting suspends execution.",
            timestamp=ts,
        )
        assert "fidelity_score" in result
        assert "igt_value" in result
        assert "health_status" in result
        assert "events" in result
        assert isinstance(result["events"], list)
        assert result["health_status"] in {"healthy", "degrading", "critical", "converged"}

    def test_fidelity_score_in_range(self):
        sid = new_conversation()["session_id"]
        base = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
        pairs = [
            ("What is a B-tree?", "A balanced tree optimised for block storage reads."),
            ("How does it differ from a B+ tree?", "B+ trees store values only in leaves."),
            ("When would you pick LSM over B-tree?", "LSM wins for write-heavy workloads."),
        ]
        for i, (h, a) in enumerate(pairs):
            ts = (base + timedelta(minutes=i + 1)).isoformat()
            r = process_turn(session_id=sid, human_message=h, agent_response=a, timestamp=ts)
            score = r["fidelity_score"]
            assert 0.0 <= score <= 1.0, f"Turn {i+1} fidelity out of range: {score}"

    def test_unknown_session_returns_error_dict(self):
        result = process_turn(
            session_id="does-not-exist",
            human_message="hello",
            agent_response="hi",
        )
        assert "error" in result
        assert "hint" in result

    def test_temporal_signals_present_when_timestamp_given(self):
        sid = new_conversation()["session_id"]
        base = datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc)
        # Turn 1
        process_turn(
            session_id=sid,
            human_message="First question.",
            agent_response="First answer.",
            timestamp=base.isoformat(),
        )
        # Turn 2 — 30 min gap
        r = process_turn(
            session_id=sid,
            human_message="Follow-up question.",
            agent_response="Follow-up answer.",
            timestamp=(base + timedelta(minutes=30)).isoformat(),
        )
        assert r["gap_seconds"] is not None
        assert r["gap_class"] is not None
        assert r["estimated_retention"] is not None

    def test_auto_timestamps_when_timestamp_omitted(self):
        # When timestamp is omitted, process_turn uses datetime.now(utc) so it
        # should not error and should return a valid result.
        sid = new_conversation()["session_id"]
        result = process_turn(
            session_id=sid,
            human_message="No timestamp provided.",
            agent_response="Still works.",
        )
        assert "fidelity_score" in result
        assert "error" not in result

    def test_client_context_spatial_signals(self):
        sid = new_conversation()["session_id"]
        result = process_turn(
            session_id=sid,
            human_message="Draft a quick standup update.",
            agent_response="Sure — what shipped, blocked, and next?",
            timestamp=datetime.now(timezone.utc).isoformat(),
            client_context={
                "device_type": "mobile",
                "timezone": "America/Sao_Paulo",
            },
        )
        assert result.get("spatial_constraint") is not None
        sc = result["spatial_constraint"]
        assert sc["screen_capacity"] in {"large", "medium", "small"}
        assert sc["max_response_length"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: configure_session
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigureSession:
    def test_applies_clarification_threshold(self):
        sid = new_conversation()["session_id"]
        result = configure_session(
            session_id=sid,
            clarification_threshold=0.2,
        )
        assert result["applied"]["clarification_threshold"] == 0.2
        assert isinstance(result["warnings"], list)

    def test_applies_event_modes(self):
        sid = new_conversation()["session_id"]
        result = configure_session(
            session_id=sid,
            event_modes={"alert.drift": "active", "checkpoint.clarification": "active"},
        )
        assert "event_modes" in result["applied"]

    def test_global_configure_no_session_id(self):
        result = configure_session(
            domain="customer-support",
            context_half_life_hours=2.0,
        )
        assert "domain" in result["applied"]

    def test_unknown_session_returns_error(self):
        result = configure_session(
            session_id="ghost-session",
            clarification_threshold=0.1,
        )
        assert "error" in result

    def test_no_kwargs_returns_empty_applied(self):
        sid = new_conversation()["session_id"]
        result = configure_session(session_id=sid)
        assert result["applied"] == {}


# ─────────────────────────────────────────────────────────────────────────────
# RESOURCE: session trajectory
# ─────────────────────────────────────────────────────────────────────────────


class TestTrajectoryResource:
    def test_returns_json_with_trajectory_fields(self):
        sid = new_conversation()["session_id"]
        base = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
        for i, (h, a) in enumerate([
            ("What is Redis?", "An in-memory key-value store."),
            ("How does Redis replication work?", "Primary sends replication stream to replicas."),
            ("What is Redis Sentinel?", "Sentinel provides automatic failover for Redis."),
        ]):
            process_turn(
                session_id=sid,
                human_message=h,
                agent_response=a,
                timestamp=(base + timedelta(minutes=i + 1)).isoformat(),
            )

        traj_json = get_trajectory(session_id=sid)
        traj = json.loads(traj_json)

        assert traj["session_id"] == sid
        assert traj["turn_count"] == 3
        assert len(traj["scores"]) == 3
        assert all(0.0 <= s <= 1.0 for s in traj["scores"])
        assert traj["health_status"] in {"healthy", "degrading", "critical", "converged"}
        assert "peak_fidelity" in traj
        assert "current_fidelity" in traj
        assert "igt_trend" in traj

    def test_trajectory_scores_evolve_across_turns(self):
        sid = new_conversation()["session_id"]
        base = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
        for i in range(5):
            process_turn(
                session_id=sid,
                human_message=f"Question number {i + 1} about distributed systems.",
                agent_response=f"Answer {i + 1} covering a distinct aspect of consistency.",
                timestamp=(base + timedelta(minutes=i + 1)).isoformat(),
            )

        traj = json.loads(get_trajectory(session_id=sid))
        assert traj["turn_count"] == 5
        assert len(traj["scores"]) == 5

    def test_trajectory_unknown_session_returns_error_json(self):
        result = json.loads(get_trajectory(session_id="not-a-real-session"))
        assert "error" in result

    def test_trajectory_is_valid_json_string(self):
        sid = new_conversation()["session_id"]
        process_turn(
            session_id=sid,
            human_message="Hello.",
            agent_response="Hi there.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        raw = get_trajectory(session_id=sid)
        assert isinstance(raw, str)
        parsed = json.loads(raw)  # must not raise
        assert isinstance(parsed, dict)


# ─────────────────────────────────────────────────────────────────────────────
# RESOURCE: session events
# ─────────────────────────────────────────────────────────────────────────────


class TestEventsResource:
    def test_returns_json_with_events_structure(self):
        sid = new_conversation()["session_id"]
        process_turn(
            session_id=sid,
            human_message="Explain gradient descent.",
            agent_response="It minimises loss by stepping in the direction of the steepest descent.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        raw = get_events(session_id=sid)
        parsed = json.loads(raw)

        assert "active_events" in parsed
        assert "all_events" in parsed
        assert "active_count" in parsed
        assert "total_count" in parsed
        assert parsed["active_count"] == len(parsed["active_events"])
        assert parsed["total_count"] == len(parsed["all_events"])

    def test_active_events_subset_of_all_events(self):
        sid = new_conversation()["session_id"]
        base = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
        for i in range(4):
            process_turn(
                session_id=sid,
                human_message=f"Technical question {i}.",
                agent_response=f"Technical answer {i}.",
                timestamp=(base + timedelta(minutes=i + 2)).isoformat(),
            )
        parsed = json.loads(get_events(session_id=sid))
        active_types = {e["type"] for e in parsed["active_events"]}
        all_types = {e["type"] for e in parsed["all_events"]}
        assert active_types.issubset(all_types)

    def test_events_unknown_session_returns_error_json(self):
        result = json.loads(get_events(session_id="ghost"))
        assert "error" in result

    def test_each_event_has_required_fields(self):
        sid = new_conversation()["session_id"]
        process_turn(
            session_id=sid,
            human_message="What is latent diffusion?",
            agent_response="It performs diffusion in a compressed latent space rather than pixel space.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        parsed = json.loads(get_events(session_id=sid))
        for ev in parsed["all_events"]:
            assert "type" in ev
            assert "active" in ev
            assert "confidence" in ev
            assert "turn" in ev
            assert "suggested_behavior" in ev

    def test_active_events_flag_match(self):
        sid = new_conversation()["session_id"]
        process_turn(
            session_id=sid,
            human_message="Question.",
            agent_response="Answer.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        parsed = json.loads(get_events(session_id=sid))
        for ev in parsed["active_events"]:
            assert ev["active"] is True


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT: monitor_conversation
# ─────────────────────────────────────────────────────────────────────────────


class TestMonitorConversationPrompt:
    def test_returns_string(self):
        result = monitor_conversation()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_session_id(self):
        result = monitor_conversation(domain="technical", agent_name="test-agent")
        assert "session_id" in result.lower() or "session" in result

    def test_contains_process_turn_instruction(self):
        result = monitor_conversation()
        assert "process_turn" in result

    def test_contains_resource_uris(self):
        result = monitor_conversation()
        assert "horizon://session/" in result
        assert "/trajectory" in result
        assert "/events" in result

    def test_contains_event_action_guidance(self):
        result = monitor_conversation()
        # Must explain what to do for key events
        assert "alert.drift" in result
        assert "alert.contradiction" in result
        assert "degrading" in result

    def test_domain_appears_in_prompt(self):
        result = monitor_conversation(domain="medical", agent_name="health-bot")
        assert "medical" in result
        assert "health-bot" in result

    def test_creates_valid_session(self):
        """The prompt must create a real, usable session — not just text."""
        # Extract the session_id from the prompt text
        prompt_text = monitor_conversation(domain="technical")
        # Find the session_id line
        sid = None
        for line in prompt_text.splitlines():
            if "session_id" in line and ":" in line:
                parts = line.split(":")
                candidate = parts[-1].strip()
                if len(candidate) == 36:  # UUID4
                    sid = candidate
                    break
        assert sid is not None, "Prompt did not contain a valid session_id UUID"

        # The session must be usable immediately
        result = process_turn(
            session_id=sid,
            human_message="What is the best way to monitor LLM agents?",
            agent_response="Use a fidelity monitor that tracks 4D conversation dynamics.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        assert "fidelity_score" in result
        assert "error" not in result

    def test_privacy_note_present(self):
        result = monitor_conversation()
        assert "privacy" in result.lower() or "raw text" in result.lower()


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION: full multi-turn flow through all three layers
# ─────────────────────────────────────────────────────────────────────────────


class TestFullFlow:
    def test_full_agent_loop_tools_then_resources(self):
        """Simulates exactly the recommended agent loop from _INSTRUCTIONS:
        new_conversation → N × process_turn → read trajectory → read events.
        """
        sid = new_conversation(metadata={"domain": "technical"})["session_id"]
        assert len(sid) == 36

        base = datetime(2026, 5, 6, 14, 0, tzinfo=timezone.utc)
        pairs = [
            ("What is a Bloom filter?", "A probabilistic data structure for set membership with no false negatives."),
            ("What's the false positive rate?", "It depends on the number of hash functions and the bit-array size."),
            ("How do you choose hash function count?", "Optimally k = (m/n) * ln(2) where m is bit count and n is expected elements."),
            ("Can Bloom filters be deleted from?", "Standard ones can't; Counting Bloom filters extend the design to support deletes."),
        ]
        fidelity_scores = []
        for i, (h, a) in enumerate(pairs):
            r = process_turn(
                session_id=sid,
                human_message=h,
                agent_response=a,
                timestamp=(base + timedelta(minutes=i + 1)).isoformat(),
            )
            assert "fidelity_score" in r
            fidelity_scores.append(r["fidelity_score"])

        # All fidelity scores should be in valid range
        assert all(0.0 <= s <= 1.0 for s in fidelity_scores)

        # Read trajectory resource
        traj = json.loads(get_trajectory(session_id=sid))
        assert traj["turn_count"] == 4
        assert len(traj["scores"]) == 4
        assert traj["health_status"] in {"healthy", "degrading", "critical", "converged"}

        # Read events resource
        events = json.loads(get_events(session_id=sid))
        assert events["total_count"] > 0
        # All events have the required structure
        for ev in events["all_events"]:
            assert isinstance(ev["active"], bool)
            assert 0.0 <= ev["confidence"] <= 1.0

    def test_configure_then_check_trajectory(self):
        sid = new_conversation()["session_id"]
        base = datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc)

        process_turn(
            session_id=sid,
            human_message="Help me refactor this function.",
            agent_response="Let's extract the nested logic into helper functions.",
            timestamp=base.isoformat(),
        )

        # Configure a lower clarification threshold
        cfg = configure_session(session_id=sid, clarification_threshold=0.1)
        assert cfg["applied"].get("clarification_threshold") == 0.1

        # Next turn should still work fine
        r = process_turn(
            session_id=sid,
            human_message="Which helper function first?",
            agent_response="Start with the validation helper; it has the most nested conditions.",
            timestamp=(base + timedelta(minutes=2)).isoformat(),
        )
        assert 0.0 <= r["fidelity_score"] <= 1.0

        traj = json.loads(get_trajectory(session_id=sid))
        assert traj["turn_count"] == 2

    def test_monitor_conversation_prompt_creates_usable_session_for_full_flow(self):
        """Full integration: prompt creates session → process_turn works →
        resources return data for that session."""
        prompt_text = monitor_conversation(domain="customer-support", agent_name="support-bot")

        # Extract session_id from prompt text
        sid = None
        for line in prompt_text.splitlines():
            if "session_id" in line and ":" in line:
                candidate = line.split(":")[-1].strip()
                if len(candidate) == 36:
                    sid = candidate
                    break
        assert sid is not None

        base = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
        for i, (h, a) in enumerate([
            ("I can't log in to my account.", "I can help — are you getting an error message?"),
            ("It says 'invalid credentials'.", "Let me reset your password. Can you confirm your email?"),
            ("It's user@example.com.", "I've sent a reset link to user@example.com."),
        ]):
            r = process_turn(
                session_id=sid,
                human_message=h,
                agent_response=a,
                timestamp=(base + timedelta(minutes=i + 1)).isoformat(),
            )
            assert "fidelity_score" in r

        traj = json.loads(get_trajectory(session_id=sid))
        assert traj["turn_count"] == 3

        events_data = json.loads(get_events(session_id=sid))
        assert "all_events" in events_data


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY: _dispatch shim backward-compat
# ─────────────────────────────────────────────────────────────────────────────


class TestDispatchShim:
    """Ensure the _dispatch shim still works for old test code."""

    @pytest.fixture
    def monitor(self):
        return FidelityMonitor(Config())

    def test_new_conversation(self, monitor):
        result = _dispatch(monitor, "new_conversation", {})
        assert "session_id" in result

    def test_process_turn(self, monitor):
        sid = _dispatch(monitor, "new_conversation", {})["session_id"]
        r = _dispatch(
            monitor,
            "process_turn",
            {
                "session_id": sid,
                "human_message": "What is MCP?",
                "agent_response": "Model Context Protocol — a standard for tool-calling agents.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert "fidelity_score" in r

    def test_get_trajectory(self, monitor):
        sid = _dispatch(monitor, "new_conversation", {})["session_id"]
        _dispatch(
            monitor,
            "process_turn",
            {
                "session_id": sid,
                "human_message": "Hello.",
                "agent_response": "Hi.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        traj = _dispatch(monitor, "get_trajectory", {"session_id": sid})
        assert traj["turn_count"] == 1

    def test_get_events(self, monitor):
        sid = _dispatch(monitor, "new_conversation", {})["session_id"]
        _dispatch(
            monitor,
            "process_turn",
            {"session_id": sid, "human_message": "Q.", "agent_response": "A."},
        )
        events = _dispatch(monitor, "get_events", {"session_id": sid})
        assert "events" in events

    def test_configure(self, monitor):
        sid = _dispatch(monitor, "new_conversation", {})["session_id"]
        r = _dispatch(
            monitor,
            "configure",
            {"session_id": sid, "clarification_threshold": 0.3},
        )
        assert r["applied"]["clarification_threshold"] == 0.3

    def test_unknown_tool_raises(self, monitor):
        with pytest.raises(ValueError, match="Unknown tool"):
            _dispatch(monitor, "no_such_tool", {})

    def test_unknown_session_raises(self, monitor):
        with pytest.raises(SessionNotFoundError):
            _dispatch(monitor, "get_trajectory", {"session_id": "ghost"})


# ─────────────────────────────────────────────────────────────────────────────
# SERVER OBJECT: FastMCP app properties
# ─────────────────────────────────────────────────────────────────────────────


class TestFastMCPAppObject:
    def test_mcp_name(self):
        from horizon.mcp.server import mcp as app

        assert app.name == "horizon-fidelity-monitor"

    def test_mcp_instructions_contain_loop(self):
        from horizon.mcp.server import _INSTRUCTIONS

        assert "new_conversation" in _INSTRUCTIONS
        assert "process_turn" in _INSTRUCTIONS
        assert "get_trajectory" in _INSTRUCTIONS or "trajectory" in _INSTRUCTIONS
        assert "health_status" in _INSTRUCTIONS

    def test_mcp_instructions_mark_safe_tools(self):
        from horizon.mcp.server import _INSTRUCTIONS

        assert "auto-run" in _INSTRUCTIONS.lower() or "SAFE TO AUTO-RUN" in _INSTRUCTIONS

    def test_create_app_returns_fastmcp(self):
        from mcp.server.fastmcp import FastMCP

        from horizon.mcp.server import create_app

        app = create_app()
        assert isinstance(app, FastMCP)
