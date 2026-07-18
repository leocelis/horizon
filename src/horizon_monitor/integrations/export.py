"""Export session data to JSON, LangSmith, Langfuse, OpenTelemetry, or Arize."""

from __future__ import annotations

import dataclasses
from typing import Any

from horizon.models import ExportResult
from horizon.session import Session


def export_session(
    session: Session,
    target: str,
    connection: Any | None = None,
) -> ExportResult:
    """Export all turn data and events for a session.

    Supported targets:
        'json'      — return JSON-serialisable dict (no connection required)
        'langsmith' — push runs to LangSmith (requires connection dict with api_key)
        'langfuse'  — push traces to Langfuse (requires connection dict with public_key/secret)
        'otel'      — emit OpenTelemetry spans (requires connection with endpoint)
        'arize'     — log records to Arize AX (requires connection with
                      space_id, api_key, model_id; model_version optional)

    Returns ExportResult with status and record count.
    """
    if target == "json":
        return _export_json(session)
    if target == "langsmith":
        return _export_langsmith(session, connection)
    if target == "langfuse":
        return _export_langfuse(session, connection)
    if target == "otel":
        return _export_otel(session, connection)
    if target == "arize":
        return _export_arize(session, connection)

    return ExportResult(
        status="failed",
        records_exported=0,
        target=target,
        errors=[
            f"Unknown export target: '{target}'. "
            "Supported: json, langsmith, langfuse, otel, arize"
        ],
    )


def _build_payload(session: Session) -> list[dict]:
    """Serialise all turn states to JSON-compatible dicts."""
    records = []
    for turn in session.turns:
        events = [dataclasses.asdict(e) for e in session.event_log if e.turn == turn.turn_number]
        records.append(
            {
                "turn_number": turn.turn_number,
                "timestamp": turn.timestamp,
                "fidelity_score": turn.fidelity_score,
                "igt_value": turn.igt_value,
                "divergence_score": turn.divergence_score,
                "twr_value": turn.twr_value,
                "consistency_score": turn.consistency_score,
                "epsilon_t": turn.epsilon_t,
                "in_context": turn.in_context,
                "events": events,
            }
        )
    return records


def _export_json(session: Session) -> ExportResult:
    """Return JSON-compatible export dict (stored in target_url as None; data embedded)."""
    records = _build_payload(session)
    return ExportResult(
        status="success",
        records_exported=len(records),
        target="json",
        target_url=None,
        errors=[],
    )


def get_json_data(session: Session) -> dict:
    """Return the full export payload as a plain dict. Useful for logging."""
    return {
        "session_id": session.session_id,
        "turn_count": session.turn_count,
        "turns": _build_payload(session),
        "fidelity_trajectory": list(session.fidelity_trajectory),
        "detected_mode": session.detected_mode,
    }


def _export_langsmith(session: Session, connection: dict | None) -> ExportResult:
    """Push turns to LangSmith as run records."""
    if not connection or "api_key" not in connection:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="langsmith",
            errors=["connection must include 'api_key'"],
        )
    try:
        from langsmith import Client

        client = Client(api_key=connection["api_key"])
        records = _build_payload(session)
        for rec in records:
            client.create_run(
                name=f"horizon_turn_{rec['turn_number']}",
                inputs={"turn_data": rec},
                run_type="chain",
            )
        return ExportResult(
            status="success",
            records_exported=len(records),
            target="langsmith",
        )
    except Exception as exc:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="langsmith",
            errors=[str(exc)],
        )


def _export_langfuse(session: Session, connection: dict | None) -> ExportResult:
    """Push turns to Langfuse as traces."""
    if not connection or "public_key" not in connection or "secret_key" not in connection:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="langfuse",
            errors=["connection must include 'public_key' and 'secret_key'"],
        )
    try:
        from langfuse import Langfuse

        lf = Langfuse(
            public_key=connection["public_key"],
            secret_key=connection["secret_key"],
            host=connection.get("host", "https://cloud.langfuse.com"),
        )
        records = _build_payload(session)
        trace = lf.trace(name=f"horizon_{session.session_id}", id=session.session_id)
        for rec in records:
            trace.span(name=f"turn_{rec['turn_number']}", input=rec)
        lf.flush()
        return ExportResult(
            status="success",
            records_exported=len(records),
            target="langfuse",
        )
    except Exception as exc:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="langfuse",
            errors=[str(exc)],
        )


def _export_otel(session: Session, connection: dict | None) -> ExportResult:
    """Emit OpenTelemetry spans for each turn."""
    if not connection or "endpoint" not in connection:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="otel",
            errors=["connection must include 'endpoint'"],
        )
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=connection["endpoint"])
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer("horizon")

        records = _build_payload(session)
        with tracer.start_as_current_span(f"horizon.session.{session.session_id}"):
            for rec in records:
                with tracer.start_as_current_span(f"horizon.turn.{rec['turn_number']}") as span:
                    for k, v in rec.items():
                        if isinstance(v, (str, int, float, bool)):
                            span.set_attribute(f"horizon.{k}", v)

        return ExportResult(
            status="success",
            records_exported=len(records),
            target="otel",
        )
    except Exception as exc:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="otel",
            errors=[str(exc)],
        )


def _export_arize(session: Session, connection: dict | None) -> ExportResult:
    """Log per-turn Horizon metrics to Arize AX as production inference records.

    Requires ``pip install horizon-monitor[arize]``.

    Connection dict fields:
        space_id (required)   — Arize space identifier
        api_key (required)    — Arize API key
        model_id (required)   — logical model name in Arize (e.g. "my-agent")
        model_version (opt)   — defaults to "horizon-v1"
        environment (opt)     — "production" | "staging" | "development"
    """
    required = {"space_id", "api_key", "model_id"}
    if not connection or not required.issubset(connection):
        missing = sorted(required - set(connection or {}))
        return ExportResult(
            status="failed",
            records_exported=0,
            target="arize",
            errors=[f"connection must include {missing}"],
        )
    try:
        import pandas as pd
        from arize.pandas.logger import Client, Schema
        from arize.utils.types import Environments, ModelTypes

        records = _build_payload(session)
        if not records:
            return ExportResult(
                status="success",
                records_exported=0,
                target="arize",
            )

        env_name = connection.get("environment", "production").upper()
        environment = getattr(Environments, env_name, Environments.PRODUCTION)

        rows = []
        for rec in records:
            rows.append(
                {
                    "prediction_id": f"{session.session_id}:{rec['turn_number']}",
                    "prediction_ts": rec["timestamp"],
                    "session_id": session.session_id,
                    "turn_number": rec["turn_number"],
                    "fidelity_score": rec["fidelity_score"],
                    "igt_value": rec["igt_value"],
                    "divergence_score": rec["divergence_score"],
                    "twr_value": rec["twr_value"],
                    "consistency_score": rec["consistency_score"],
                    "epsilon_t": rec["epsilon_t"],
                    "in_context": bool(rec["in_context"]),
                    "event_count": len(rec["events"]),
                }
            )
        df = pd.DataFrame(rows)

        schema = Schema(
            prediction_id_column_name="prediction_id",
            timestamp_column_name="prediction_ts",
            prediction_score_column_name="fidelity_score",
            feature_column_names=[
                "turn_number",
                "igt_value",
                "divergence_score",
                "twr_value",
                "consistency_score",
                "epsilon_t",
                "in_context",
                "event_count",
            ],
            tag_column_names=["session_id"],
        )

        client = Client(
            space_id=connection["space_id"],
            api_key=connection["api_key"],
        )
        client.log(
            dataframe=df,
            model_id=connection["model_id"],
            model_version=connection.get("model_version", "horizon-v1"),
            model_type=ModelTypes.SCORE_CATEGORICAL,
            environment=environment,
            schema=schema,
        )

        return ExportResult(
            status="success",
            records_exported=len(records),
            target="arize",
        )
    except Exception as exc:
        return ExportResult(
            status="failed",
            records_exported=0,
            target="arize",
            errors=[str(exc)],
        )
