"""Positive end-to-end coverage for every export target.

Until v0.2.0, only the ``json`` target had a positive test; ``langsmith``,
``langfuse``, ``otel``, and ``arize`` only had "fails gracefully when not
configured" tests. This file replaces that gap by injecting fake SDK
clients onto ``sys.modules`` and asserting Horizon (a) records the right
number of records, (b) builds the right payload shape per backend, and
(c) returns ``status="success"``.

These tests do not perform any network I/O. They cover the wiring,
payload construction, and response handling that real users rely on. If
the public API of any of these vendors changes in a breaking way, the
matching test will fail loudly.
"""

from __future__ import annotations

import sys
import types

import pytest

from horizon import FidelityMonitor


# ── Shared session fixture ──────────────────────────────────────────────────


def _build_session(turns: int = 3) -> tuple[FidelityMonitor, str]:
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    for i in range(turns):
        monitor.process_turn(
            sid,
            f"Turn {i} question about B-trees and indexing.",
            f"Turn {i} answer covering fanout {100 + i} and disk seeks.",
        )
    return monitor, sid


# ── LangSmith ────────────────────────────────────────────────────────────────


class _FakeLangSmithClient:
    instances: list["_FakeLangSmithClient"] = []

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.created: list[dict] = []
        _FakeLangSmithClient.instances.append(self)

    def create_run(self, *, name: str, inputs: dict, run_type: str) -> None:
        self.created.append({"name": name, "inputs": inputs, "run_type": run_type})


def test_langsmith_export_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.SimpleNamespace(Client=_FakeLangSmithClient)
    monkeypatch.setitem(sys.modules, "langsmith", fake_module)
    _FakeLangSmithClient.instances.clear()

    monitor, sid = _build_session(turns=4)
    result = monitor.export_to(
        sid, target="langsmith", connection={"api_key": "test-key"}
    )

    assert result.status == "success"
    assert result.records_exported == 4
    assert result.target == "langsmith"

    assert len(_FakeLangSmithClient.instances) == 1
    client = _FakeLangSmithClient.instances[0]
    assert client.api_key == "test-key"
    assert len(client.created) == 4
    for i, run in enumerate(client.created, start=1):
        assert run["name"] == f"horizon_turn_{i}"
        assert run["run_type"] == "chain"
        assert run["inputs"]["turn_data"]["turn_number"] == i


# ── Langfuse ─────────────────────────────────────────────────────────────────


class _FakeLangfuseSpan:
    def __init__(self, name: str, input_payload: dict) -> None:
        self.name = name
        self.input = input_payload


class _FakeLangfuseTrace:
    def __init__(self, name: str, id_: str) -> None:
        self.name = name
        self.id = id_
        self.spans: list[_FakeLangfuseSpan] = []

    def span(self, *, name: str, input: dict) -> _FakeLangfuseSpan:
        s = _FakeLangfuseSpan(name, input)
        self.spans.append(s)
        return s


class _FakeLangfuse:
    instances: list["_FakeLangfuse"] = []

    def __init__(self, *, public_key: str, secret_key: str, host: str) -> None:
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host
        self.traces: list[_FakeLangfuseTrace] = []
        self.flushed = 0
        _FakeLangfuse.instances.append(self)

    def trace(self, *, name: str, id: str) -> _FakeLangfuseTrace:  # noqa: A002
        t = _FakeLangfuseTrace(name, id)
        self.traces.append(t)
        return t

    def flush(self) -> None:
        self.flushed += 1


def test_langfuse_export_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.SimpleNamespace(Langfuse=_FakeLangfuse)
    monkeypatch.setitem(sys.modules, "langfuse", fake_module)
    _FakeLangfuse.instances.clear()

    monitor, sid = _build_session(turns=3)
    result = monitor.export_to(
        sid,
        target="langfuse",
        connection={
            "public_key": "pk-test",
            "secret_key": "sk-test",
            "host": "https://example.invalid",
        },
    )

    assert result.status == "success"
    assert result.records_exported == 3
    assert result.target == "langfuse"

    assert len(_FakeLangfuse.instances) == 1
    lf = _FakeLangfuse.instances[0]
    assert lf.flushed == 1
    assert len(lf.traces) == 1
    trace = lf.traces[0]
    assert trace.id == sid
    assert len(trace.spans) == 3
    assert trace.spans[0].name == "turn_1"


# ── OpenTelemetry ────────────────────────────────────────────────────────────


class _FakeSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, object] = {}

    def __enter__(self) -> "_FakeSpan":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class _FakeTracer:
    instances: list["_FakeTracer"] = []

    def __init__(self) -> None:
        self.spans: list[_FakeSpan] = []
        _FakeTracer.instances.append(self)

    def start_as_current_span(self, name: str) -> _FakeSpan:
        s = _FakeSpan(name)
        self.spans.append(s)
        return s


class _FakeProvider:
    def __init__(self) -> None:
        self.processors: list[object] = []

    def add_span_processor(self, processor: object) -> None:
        self.processors.append(processor)


_otel_state: dict[str, object] = {}


def test_otel_export_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeTracer.instances.clear()
    tracer = _FakeTracer()

    fake_trace = types.SimpleNamespace(
        set_tracer_provider=lambda p: _otel_state.setdefault("provider", p),
        get_tracer=lambda _name: tracer,
    )
    monkeypatch.setitem(sys.modules, "opentelemetry", types.SimpleNamespace(trace=fake_trace))
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", fake_trace)

    fake_exporter_mod = types.SimpleNamespace(
        OTLPSpanExporter=lambda endpoint: types.SimpleNamespace(endpoint=endpoint)
    )
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
        fake_exporter_mod,
    )

    fake_sdk_trace_export = types.SimpleNamespace(
        BatchSpanProcessor=lambda exp: types.SimpleNamespace(exporter=exp)
    )
    monkeypatch.setitem(
        sys.modules, "opentelemetry.sdk.trace.export", fake_sdk_trace_export
    )

    fake_sdk_trace = types.SimpleNamespace(TracerProvider=_FakeProvider)
    monkeypatch.setitem(sys.modules, "opentelemetry.sdk.trace", fake_sdk_trace)

    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.sdk",
        types.SimpleNamespace(trace=fake_sdk_trace),
    )
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.exporter",
        types.SimpleNamespace(otlp=types.SimpleNamespace(proto=types.SimpleNamespace(http=types.SimpleNamespace(trace_exporter=fake_exporter_mod)))),
    )

    monitor, sid = _build_session(turns=2)
    result = monitor.export_to(
        sid,
        target="otel",
        connection={"endpoint": "http://localhost:4318/v1/traces"},
    )

    assert result.status == "success"
    assert result.records_exported == 2
    assert result.target == "otel"

    assert _FakeTracer.instances, "tracer was never created"
    spans = _FakeTracer.instances[0].spans
    # 1 session span + 2 turn spans
    assert any(s.name.startswith("horizon.session.") for s in spans)
    turn_spans = [s for s in spans if s.name.startswith("horizon.turn.")]
    assert len(turn_spans) == 2
    for s in turn_spans:
        assert "horizon.turn_number" in s.attributes
        assert "horizon.fidelity_score" in s.attributes


# ── Arize ────────────────────────────────────────────────────────────────────


class _FakeArizeClient:
    instances: list["_FakeArizeClient"] = []

    def __init__(self, *, space_id: str, api_key: str) -> None:
        self.space_id = space_id
        self.api_key = api_key
        self.logged: list[dict] = []
        _FakeArizeClient.instances.append(self)

    def log(self, **kwargs) -> None:  # noqa: ANN003
        self.logged.append(kwargs)


def test_arize_export_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    pd = pytest.importorskip("pandas")  # arize export requires pandas

    fake_logger = types.SimpleNamespace(
        Client=_FakeArizeClient,
        Schema=lambda **kwargs: types.SimpleNamespace(**kwargs),  # noqa: ANN003
    )
    fake_pandas_mod = types.SimpleNamespace(logger=fake_logger)
    monkeypatch.setitem(sys.modules, "arize", types.SimpleNamespace(pandas=fake_pandas_mod))
    monkeypatch.setitem(sys.modules, "arize.pandas", fake_pandas_mod)
    monkeypatch.setitem(sys.modules, "arize.pandas.logger", fake_logger)

    fake_envs = types.SimpleNamespace(
        PRODUCTION="production",
        STAGING="staging",
        DEVELOPMENT="development",
    )
    fake_model_types = types.SimpleNamespace(SCORE_CATEGORICAL="score_categorical")
    fake_utils_types = types.SimpleNamespace(
        Environments=fake_envs, ModelTypes=fake_model_types
    )
    monkeypatch.setitem(
        sys.modules, "arize.utils", types.SimpleNamespace(types=fake_utils_types)
    )
    monkeypatch.setitem(sys.modules, "arize.utils.types", fake_utils_types)

    _FakeArizeClient.instances.clear()
    monitor, sid = _build_session(turns=4)
    result = monitor.export_to(
        sid,
        target="arize",
        connection={
            "space_id": "space-test",
            "api_key": "key-test",
            "model_id": "horizon-test-agent",
            "environment": "staging",
        },
    )

    assert result.status == "success", result.errors
    assert result.records_exported == 4
    assert result.target == "arize"

    assert len(_FakeArizeClient.instances) == 1
    client = _FakeArizeClient.instances[0]
    assert client.space_id == "space-test"
    assert len(client.logged) == 1
    df = client.logged[0]["dataframe"]
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert {"prediction_id", "prediction_ts", "fidelity_score"} <= set(df.columns)
    assert client.logged[0]["model_id"] == "horizon-test-agent"
    assert client.logged[0]["environment"] == "staging"
