"""Memento Mori — the mission plane.

A second, optional measurement plane whose unit of analysis is the *mission*
(a goal with a clock) rather than the conversation. It performs elapsed-time
**accounting** — ages, TTL states, deferral expiry, per-entity latency,
horizon share, and (only when a rate is declared) cost-of-delay and
break-even dates — as deterministic arithmetic over caller-supplied records,
and emits edge-triggered signals through the host's existing per-turn
contract.

Boundaries, all enforced by tests:

* facts are caller-provided — the engine never invents a duration, date, or
  amount, and degrades by omission rather than substitution;
* the clock path makes zero LLM calls and zero network calls, and the
  evaluation instant is always a parameter;
* signals fire on edges, never on persisting levels, and are capped;
* entity latency is reported on functional slots — never as a person score.

The plane is inert unless ``MementoConfig.store_path`` is set.

Reference: ``docs/product/MEMENTO_MORI_PRD.md``,
``docs/spec/MEMENTO_MORI_TECH_SPEC.md``,
``docs/integrations/MEMENTO_MORI_AGENTS.md``.
"""

from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.engine import evaluate
from horizon_monitor.memento.errors import (
    ArtifactProvenanceRequiredError,
    CounterfactualRefusedError,
    CurrencyConversionRefusedError,
    DuplicateRootError,
    FinancialModellingRefusedError,
    ForecastRefusedError,
    InferentialDominanceRefusedError,
    MementoError,
    NonFiniteRootError,
    PersonNamespaceUnflaggedError,
    PersonRankingRefusedError,
    RefusalError,
    RootlessItemError,
    SchemaError,
    StoreCorruptionError,
    TenantResolutionError,
    UndatedDeferralError,
)
from horizon_monitor.memento.models import (
    ClockEvent,
    ClockReport,
    EventKind,
    Item,
    ItemClock,
    ItemKind,
    Provenance,
    Signal,
    SignalReport,
    SignalState,
    StoreSnapshot,
)
from horizon_monitor.memento.signals import evaluate_signals
from horizon_monitor.memento.store import MementoStore

__all__ = [
    "ArtifactProvenanceRequiredError",
    "ClockEvent",
    "ClockReport",
    "CounterfactualRefusedError",
    "CurrencyConversionRefusedError",
    "DuplicateRootError",
    "EventKind",
    "FinancialModellingRefusedError",
    "ForecastRefusedError",
    "InferentialDominanceRefusedError",
    "Item",
    "ItemClock",
    "ItemKind",
    "MementoConfig",
    "MementoError",
    "MementoStore",
    "NonFiniteRootError",
    "PersonNamespaceUnflaggedError",
    "PersonRankingRefusedError",
    "Provenance",
    "RefusalError",
    "RootlessItemError",
    "SchemaError",
    "Signal",
    "SignalReport",
    "SignalState",
    "StoreCorruptionError",
    "TenantResolutionError",
    "StoreSnapshot",
    "UndatedDeferralError",
    "evaluate",
    "evaluate_signals",
]
