"""Typed errors for the Memento Mori plane.

Per horizon_memento_mori_intent.yaml::facts_are_caller_provided and the
per-module intents' schema/refusal constraints: every rejection is a typed
exception naming the violated rule, never a silently-coerced value and
never a generic ValueError. A failed write must leave the store byte-
identical — callers are expected to validate (which raises one of the
SchemaError subclasses below) BEFORE any row is written.

Every exception sets `.rule` and `.fix` as first-class attributes (not just
baked into the human-readable message string) so a caller — the MCP server,
in particular — can serialize `{error_type, rule, fix}` without regex-
parsing prose (test plan M-2). `.rule` names the violated constraint;
`.fix` is the actionable instruction. The message passed to
`Exception.__init__` is built from the same two pieces, so `str(exc)` is
unchanged from before this split existed.
"""

from __future__ import annotations


class MementoError(Exception):
    """Base class for every typed error the plane can raise.

    `rule` and `fix` are set by every concrete subclass's `__init__` before
    the human-readable message is composed — see module docstring.
    """

    rule: str = ""
    fix: str = ""

    def _init_message(self, error_type: str, fix: str, rule: str) -> None:
        self.fix = fix
        self.rule = rule
        super().__init__(f"{error_type}: {fix} Rule: {rule}")


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
        self._init_message(
            "UndatedDeferralError",
            fix=(
                "kind=deferral requires revisit_date; none was supplied"
                f"{f' for {item_title!r}' if item_title else ''}. "
                "No configuration flag can bypass this."
            ),
            rule="intent.non_goals — 'an undated deferral is invalid, not incomplete'.",
        )


class DuplicateRootError(SchemaError):
    """A second kind=horizon item was registered; exactly one root is allowed."""

    def __init__(self) -> None:
        self._init_message(
            "DuplicateRootError",
            fix="this store already has a kind=horizon root.",
            rule=(
                "memento_engine parent constraint finite_rooted_tree — "
                "'exactly one root item of kind=horizon' per store."
            ),
        )


class NonFiniteRootError(SchemaError):
    """A kind=horizon root was registered without a finite end_date."""

    def __init__(self) -> None:
        self._init_message(
            "NonFiniteRootError",
            fix="kind=horizon requires a finite end_date.",
            rule=(
                "finite_rooted_tree — 'a finite end date (operator-defined or "
                "derived by arithmetic from operator-supplied inputs)'."
            ),
        )


class RootlessItemError(SchemaError):
    """A non-root item's parent chain does not terminate at the single root."""

    def __init__(self, item_title: str = "") -> None:
        self._init_message(
            "RootlessItemError",
            fix=(
                "item"
                f"{f' {item_title!r}' if item_title else ''} has no parent path "
                "terminating at the store's kind=horizon root."
            ),
            rule=(
                "finite_rooted_tree — 'every other item must carry a parent "
                "path terminating at the root'."
            ),
        )


class PersonNamespaceUnflaggedError(SchemaError):
    """namespace='person' was requested without the explicit confirmation flag."""

    def __init__(self) -> None:
        self._init_message(
            "PersonNamespaceUnflaggedError",
            fix=(
                "kind=entity with namespace='person' requires the explicit "
                "person_namespace_confirmed=True argument at write time."
            ),
            rule=(
                "memento_store::person_namespace_explicit — 'slot is the "
                "default; person namespace is explicit and flagged'."
            ),
        )


class ArtifactProvenanceRequiredError(SchemaError):
    """An ARTIFACT event was recorded without complete provenance."""

    def __init__(self, missing: tuple[str, ...] = ()) -> None:
        detail = f" Missing field(s): {', '.join(missing)}." if missing else ""
        self._init_message(
            "ArtifactProvenanceRequiredError",
            fix=(
                "kind=artifact events require provenance.source_system, "
                "provenance.native_id, and provenance.raw_timestamp, all "
                f"present.{detail}"
            ),
            rule="memento_store::artifact_provenance_required.",
        )


class RetentionScopeError(SchemaError):
    """Display-name redaction was requested on a non-person entity."""

    def __init__(self, item_id: str, namespace: str | None) -> None:
        self._init_message(
            "RetentionScopeError",
            fix=(
                f"redact_person_display_name applies only to person-namespace "
                f"entities; {item_id!r} is namespace={namespace!r}. Slot labels "
                "are functional, not personal data, and are not retention-bound."
            ),
            rule=(
                "PRD 8 - a third party's display name is kept only for the open "
                "wait, with short retention after the wait ends."
            ),
        )


class StoreCorruptionError(MementoError):
    """A stored item references a parent_id that no longer resolves.

    Per intent v0.7 clarification: store corruption (orphaned parent) fails
    evaluation LOUDLY — never a silent skip.
    """

    def __init__(self, item_id: str, missing_parent_id: str) -> None:
        self._init_message(
            "StoreCorruptionError",
            fix=(
                f"item {item_id!r} references parent_id {missing_parent_id!r}, "
                "which does not exist in this store. The horizon tree is "
                "corrupted; evaluation refuses to proceed silently."
            ),
            rule="intent v0.7 clarification #3.",
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
        self._init_message(
            "FinancialModellingRefusedError",
            fix=(
                "the engine performs no financial modelling"
                f"{f' ({requested})' if requested else ''}."
            ),
            rule=(
                "intent non_goals — 'no NPV, IRR, discounted cash flow, "
                "discount-rate selection, amortisation schedules'. Monetary "
                "outputs are limited to products/sums/quotients of stored "
                "amounts, the stored rate, and stored/derived durations."
            ),
        )


class CurrencyConversionRefusedError(RefusalError):
    """A currency conversion was requested."""

    def __init__(self) -> None:
        self._init_message(
            "CurrencyConversionRefusedError",
            fix="the engine performs no currency conversion; rate_currency is a label only.",
            rule="intent non_goals — 'no currency conversion, no tax'.",
        )


class ForecastRefusedError(RefusalError):
    """A forecast of an unmeasured duration, rate, or savings was requested."""

    def __init__(self, quantity: str = "a value") -> None:
        self._init_message(
            "ForecastRefusedError",
            fix=f"{quantity} was requested without a measured record to derive it from.",
            rule=(
                "facts_are_caller_provided — 'the engine never generates, "
                "estimates, or infers a duration, a future date, or a "
                "monetary amount from anything except arithmetic over "
                "caller-supplied records'."
            ),
        )


class CounterfactualRefusedError(RefusalError):
    """A 'what the untaken path would have cost' computation was requested."""

    def __init__(self) -> None:
        self._init_message(
            "CounterfactualRefusedError",
            fix=(
                "the engine has no 'would-have-taken' computation. The honest "
                "substitute is the incumbent's accruing measured delay "
                "(signal.path_ahead)."
            ),
            rule=(
                "intent non_goals — 'counterfactual accounting: the plane "
                "never states what an untaken path would have cost'."
            ),
        )


class InferentialDominanceRefusedError(RefusalError):
    """A p-value / confidence interval / posterior / sequential test was requested
    on path latencies."""

    def __init__(self) -> None:
        self._init_message(
            "InferentialDominanceRefusedError",
            fix=(
                "the engine emits no inferential 'path A beats path B' "
                "distributional claim — no p-value, confidence interval, "
                "posterior, or sequential/always-valid test on path "
                "latencies. Only signal.path_ahead (descriptive two-clock "
                "predicate) is computed."
            ),
            rule="research topic B9 / intent v0.5 signal redesign; PRD §3.2, §7.",
        )


class PersonRankingRefusedError(RefusalError):
    """A person-ordered ranking or comparison was requested."""

    def __init__(self) -> None:
        self._init_message(
            "PersonRankingRefusedError",
            fix="the engine never ranks, scores, or orders identifiable people.",
            rule=(
                "intent non_goals — 'people analytics ... agents must not "
                "rank people in suggested_behavior'."
            ),
        )
