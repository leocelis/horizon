"""Typed errors for the Memento Mori plane.

Per horizon_memento_mori_intent.yaml::facts_are_caller_provided and the
per-module intents' schema/refusal constraints: every rejection is a typed
exception naming the violated rule, never a silently-coerced value and
never a generic ValueError. A failed write must leave the store byte-
identical — callers are expected to validate (which raises one of the
SchemaError subclasses below) BEFORE any row is written.
"""

from __future__ import annotations


class MementoError(Exception):
    """Base class for every typed error the plane can raise."""


# ── Schema errors (store write-path rejections; no override flag exists) ───


class SchemaError(MementoError):
    """Base class for store write-path schema violations."""


class UndatedDeferralError(SchemaError):
    """A deferral was registered without a revisit_date.

    horizon_memento_mori_intent.yaml::facts_are_caller_provided —
    "an undated deferral is rejected at the schema with no configuration
    override".
    """

    def __init__(self, item_title: str = "") -> None:
        super().__init__(
            "UndatedDeferralError: kind=deferral requires revisit_date; "
            f"none was supplied{f' for {item_title!r}' if item_title else ''}. "
            "Rule: intent.non_goals — 'an undated deferral is invalid, not "
            "incomplete'. No configuration flag can bypass this."
        )


class DuplicateRootError(SchemaError):
    """A second kind=horizon item was registered; exactly one root is allowed."""

    def __init__(self) -> None:
        super().__init__(
            "DuplicateRootError: this store already has a kind=horizon root. "
            "Rule: memento_engine parent constraint finite_rooted_tree — "
            "'exactly one root item of kind=horizon' per store."
        )


class NonFiniteRootError(SchemaError):
    """A kind=horizon root was registered without a finite end_date."""

    def __init__(self) -> None:
        super().__init__(
            "NonFiniteRootError: kind=horizon requires a finite end_date. "
            "Rule: finite_rooted_tree — 'a finite end date (operator-defined "
            "or derived by arithmetic from operator-supplied inputs)'."
        )


class RootlessItemError(SchemaError):
    """A non-root item's parent chain does not terminate at the single root."""

    def __init__(self, item_title: str = "") -> None:
        super().__init__(
            "RootlessItemError: item"
            f"{f' {item_title!r}' if item_title else ''} has no parent path "
            "terminating at the store's kind=horizon root. Rule: "
            "finite_rooted_tree — 'every other item must carry a parent path "
            "terminating at the root'."
        )


class PersonNamespaceUnflaggedError(SchemaError):
    """namespace='person' was requested without the explicit confirmation flag."""

    def __init__(self) -> None:
        super().__init__(
            "PersonNamespaceUnflaggedError: kind=entity with namespace='person' "
            "requires the explicit person_namespace_confirmed=True argument at "
            "write time. Rule: memento_store::person_namespace_explicit — "
            "'slot is the default; person namespace is explicit and flagged'."
        )


class ArtifactProvenanceRequiredError(SchemaError):
    """An ARTIFACT event was recorded without complete provenance."""

    def __init__(self, missing: tuple[str, ...] = ()) -> None:
        detail = f" Missing field(s): {', '.join(missing)}." if missing else ""
        super().__init__(
            "ArtifactProvenanceRequiredError: kind=artifact events require "
            "provenance.source_system, provenance.native_id, and "
            "provenance.raw_timestamp, all present." + detail + " Rule: "
            "memento_store::artifact_provenance_required."
        )


class StoreCorruptionError(MementoError):
    """A stored item references a parent_id that no longer resolves.

    Per intent v0.7 clarification: store corruption (orphaned parent) fails
    evaluation LOUDLY — never a silent skip.
    """

    def __init__(self, item_id: str, missing_parent_id: str) -> None:
        super().__init__(
            f"StoreCorruptionError: item {item_id!r} references parent_id "
            f"{missing_parent_id!r}, which does not exist in this store. "
            "The horizon tree is corrupted; evaluation refuses to proceed "
            "silently. Rule: intent v0.7 clarification #3."
        )


# ── Refusal errors (engine computation refusals) ───────────────────────────


class RefusalError(MementoError):
    """Base class for typed refusals of a requested computation.

    Per memento_engine_intent.yaml::typed_refusals: "no code path returns
    an approximation instead" — every refused request raises one of these,
    never a number.
    """


class FinancialModellingRefusedError(RefusalError):
    """NPV / IRR / DCF / discount-rate selection / amortisation was requested."""

    def __init__(self, requested: str = "") -> None:
        super().__init__(
            "FinancialModellingRefusedError: the engine performs no financial "
            f"modelling{f' ({requested})' if requested else ''}. Rule: "
            "intent non_goals — 'no NPV, IRR, discounted cash flow, "
            "discount-rate selection, amortisation schedules'. Monetary "
            "outputs are limited to products/sums/quotients of stored "
            "amounts, the stored rate, and stored/derived durations."
        )


class CurrencyConversionRefusedError(RefusalError):
    """A currency conversion was requested."""

    def __init__(self) -> None:
        super().__init__(
            "CurrencyConversionRefusedError: the engine performs no currency "
            "conversion; rate_currency is a label only. Rule: intent "
            "non_goals — 'no currency conversion, no tax'."
        )


class ForecastRefusedError(RefusalError):
    """A forecast of an unmeasured duration, rate, or savings was requested."""

    def __init__(self, quantity: str = "a value") -> None:
        super().__init__(
            f"ForecastRefusedError: {quantity} was requested without a "
            "measured record to derive it from. Rule: "
            "facts_are_caller_provided — 'the engine never generates, "
            "estimates, or infers a duration, a future date, or a monetary "
            "amount from anything except arithmetic over caller-supplied "
            "records'."
        )


class CounterfactualRefusedError(RefusalError):
    """A 'what the untaken path would have cost' computation was requested."""

    def __init__(self) -> None:
        super().__init__(
            "CounterfactualRefusedError: the engine has no 'would-have-taken' "
            "computation. Rule: intent non_goals — 'counterfactual "
            "accounting: the plane never states what an untaken path would "
            "have cost'. The honest substitute is the incumbent's accruing "
            "measured delay (signal.path_ahead)."
        )


class InferentialDominanceRefusedError(RefusalError):
    """A p-value / confidence interval / posterior / sequential test was requested
    on path latencies."""

    def __init__(self) -> None:
        super().__init__(
            "InferentialDominanceRefusedError: the engine emits no "
            "inferential 'path A beats path B' distributional claim — no "
            "p-value, confidence interval, posterior, or sequential/"
            "always-valid test on path latencies. Rule: research topic B9 "
            "/ intent v0.5 signal redesign; PRD §3.2, §7. Only "
            "signal.path_ahead (descriptive two-clock predicate) is "
            "computed."
        )


class PersonRankingRefusedError(RefusalError):
    """A person-ordered ranking or comparison was requested."""

    def __init__(self) -> None:
        super().__init__(
            "PersonRankingRefusedError: the engine never ranks, scores, or "
            "orders identifiable people. Rule: intent non_goals — 'people "
            "analytics ... agents must not rank people in "
            "suggested_behavior'."
        )
