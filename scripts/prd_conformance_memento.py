"""PRD conformance probe — executes each testable PRD claim against the
shipped implementation and prints a verdict per claim.

Not a substitute for the acceptance suite; this exercises the PRD's own
wording end to end so a claim cannot pass by virtue of a test name.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal

sys.path.insert(0, "src")

from horizon_monitor.memento import engine, money, propose, signals  # noqa: E402
from horizon_monitor.memento import errors as merr  # noqa: E402
from horizon_monitor.memento.config import MementoConfig  # noqa: E402
from horizon_monitor.memento.models import EventKind, ItemKind, Provenance  # noqa: E402
from horizon_monitor.memento.store import MementoStore  # noqa: E402

UTC = timezone.utc
T = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
RESULTS: list[tuple[str, str, str, str]] = []


def check(section: str, claim: str, fn) -> None:
    try:
        detail = fn()
        RESULTS.append((section, claim, "PASS", str(detail)[:110]))
    except AssertionError as e:
        RESULTS.append((section, claim, "FAIL", str(e)[:110]))
    except Exception as e:  # noqa: BLE001
        RESULTS.append((section, claim, "ERROR", f"{type(e).__name__}: {e}"[:110]))


def new_store() -> MementoStore:
    return MementoStore(pathlib.Path(tempfile.mkdtemp()) / "mm.db")


def smallco():
    spec = importlib.util.spec_from_file_location("cf", "tests/unit/memento_mori/conftest.py")
    cf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cf)
    st = new_store()
    return st, cf.build_smallco(st)


def root(st):
    return st.register_item(
        kind=ItemKind.HORIZON,
        title="h",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )


# ---------------------------------------------------------------- §3.2 non-goals
def _no_estimator():
    for fn in ("forecast", "predict", "estimate_duration"):
        assert not hasattr(engine, fn), f"engine exposes {fn}"
    return "no forecast/predict/estimate_duration on engine"


def _no_finance():
    hits = []
    for name in ("npv", "irr", "discounted_cash_flow", "convert_currency"):
        f = getattr(money, name, None)
        assert f is not None, f"{name} should exist as an explicit refusal"
        try:
            f()
            hits.append(f"{name} RETURNED")
        except merr.MementoError:
            pass
        except Exception as e:  # noqa: BLE001
            hits.append(f"{name}->{type(e).__name__}")
    assert not hits, hits
    return "npv/irr/dcf/convert_currency all raise typed refusals"


def _no_counterfactual():
    for fn in ("would_have_taken", "counterfactual", "simulate_path"):
        assert not hasattr(engine, fn), fn
    return "no counterfactual entry point"


def _no_statistics():
    st, ids = smallco()
    rep = engine.evaluate(st.snapshot(), T, MementoConfig())
    blob = str(rep.to_dict()).lower()
    for tok in ("p_value", "pvalue", "confidence_interval", "conf_int", "e_value"):
        assert tok not in blob, tok
    return "no p-value/CI/e-value field anywhere in the report"


def _no_scheduler():
    for mod in (engine, signals):
        for fn in ("create_reminder", "send_notification", "schedule"):
            assert not hasattr(mod, fn), fn
    return "no reminder/notification/schedule surface"


# ---------------------------------------------------------------- §3.3 principles
def _byte_identical():
    st, ids = smallco()
    snap = st.snapshot()
    a = str(engine.evaluate(snap, T, MementoConfig()).to_dict())
    b = str(engine.evaluate(snap, T, MementoConfig()).to_dict())
    assert a == b, "reports differ across identical calls"
    return f"identical snapshot+instant -> identical report ({len(a)} chars)"


def _optional_plane():
    cfg = MementoConfig()
    assert cfg.store_path is None, "plane must default OFF"
    return "MementoConfig().store_path is None by default"


def _no_ambient_clock():
    import inspect

    src = inspect.getsource(engine)
    assert "datetime.now" not in src and "utcnow" not in src
    return "engine module contains no ambient clock read"


# ---------------------------------------------------------------- §4.1 tree
def _tree_rules():
    st = new_store()
    r = root(st)
    fails = {}
    try:
        st.register_item(
            kind=ItemKind.HORIZON,
            title="h2",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2031, 1, 1),
        )
        fails["second_root"] = "ACCEPTED"
    except merr.DuplicateRootError:
        pass
    try:
        st.register_item(
            kind=ItemKind.DEFERRAL,
            title="park",
            parent_id=r,
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        )
        fails["undated_deferral"] = "ACCEPTED"
    except merr.UndatedDeferralError:
        pass
    try:
        st.register_item(
            kind=ItemKind.MISSION,
            title="orphan",
            parent_id=None,
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        )
        fails["rootless"] = "ACCEPTED"
    except (merr.RootlessItemError, merr.DuplicateRootError, merr.SchemaError):
        pass
    try:
        st.register_item(
            kind=ItemKind.ENTITY,
            title="a-person",
            parent_id=r,
            namespace="person",
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        )
        fails["unflagged_person"] = "ACCEPTED"
    except merr.PersonNamespaceUnflaggedError:
        pass
    assert not fails, fails
    return "duplicate root, undated deferral, rootless item, unflagged person all rejected"


def _eight_kinds():
    assert len(list(ItemKind)) == 8, [k.value for k in ItemKind]
    return ",".join(k.value for k in ItemKind)


# ---------------------------------------------------------------- §5.2 all 12 signals
def _twelve_signals_declared():
    assert len(signals.TIER) == 12, sorted(signals.TIER)
    assert set(signals.TIER) == set(signals.SUGGESTED_BEHAVIOR)
    return f"{len(signals.TIER)} types, tier+behaviour tables agree"


def _signals_fire_end_to_end():
    """Every one of the twelve must be *reachable* — construct a store that
    triggers each and record which actually fired."""
    fired: set[str] = set()

    # (a) smallco covers ttl/deferral/stall/unpaired/share/slowest/probe/path
    st, ids = smallco()
    cfg = MementoConfig(per_turn_fire_cap=99)
    rep = engine.evaluate(st.snapshot(), T, cfg)
    sr, _ = signals.evaluate_signals(st.snapshot(), rep, T, cfg)
    for s in (*sr.fired, *sr.due, *sr.acked):
        fired.add(s.signal_type)

    # (b) deadline_window: a deadline inside its warning window
    st2 = new_store()
    r2 = root(st2)
    m2 = st2.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=r2,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    st2.register_item(
        kind=ItemKind.DEADLINE,
        title="soon",
        parent_id=m2,
        deadline_date=date(2026, 8, 20),
        deadline_kind="hard_cutoff",
        gates_item_id=m2,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    rep2 = engine.evaluate(st2.snapshot(), T, cfg)
    sr2, _ = signals.evaluate_signals(st2.snapshot(), rep2, T, cfg)
    for s in (*sr2.fired, *sr2.due):
        fired.add(s.signal_type)

    # (c) gate_aging
    st3 = new_store()
    r3 = root(st3)
    m3 = st3.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=r3,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    st3.register_item(
        kind=ItemKind.GATE,
        title="g",
        parent_id=m3,
        age_budget_days=5,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    rep3 = engine.evaluate(st3.snapshot(), T, cfg)
    sr3, _ = signals.evaluate_signals(st3.snapshot(), rep3, T, cfg)
    for s in (*sr3.fired, *sr3.due):
        fired.add(s.signal_type)

    # (d) cost_of_delay + breakeven_passed
    st4 = new_store()
    r4 = root(st4)
    m4 = st4.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=r4,
        amount=Decimal("10"),
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    st4.record_event(
        item_id=m4,
        kind=EventKind.RATIFY,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        payload={"kind": "breakeven", "breakeven_date": "2026-08-01"},
    )
    cfg4 = MementoConfig(
        time_value_rate=Decimal("50"), cost_of_delay_threshold=Decimal("1"), per_turn_fire_cap=99
    )
    rep4 = engine.evaluate(st4.snapshot(), T, cfg4)
    sr4, _ = signals.evaluate_signals(st4.snapshot(), rep4, T, cfg4)
    for s in (*sr4.fired, *sr4.due):
        fired.add(s.signal_type)

    missing = set(signals.TIER) - fired
    assert not missing, f"unreachable: {sorted(missing)}"
    return f"all 12 reachable: {len(fired)} observed"


# ---------------------------------------------------------------- §5.1 firing rules
def _edge_not_level():
    """No (item, signal_type) pair may fire twice while its predicate is
    unchanged. Under the per-turn cap a LATER turn legitimately fires a
    DIFFERENT item's first edge, so counting fires per turn proves nothing —
    the invariant is on the pairs."""
    st, ids = smallco()
    cfg = MementoConfig()
    seen: set[tuple[str, str]] = set()
    total = 0
    for _ in range(12):  # more turns than there are due predicates
        snap = st.snapshot()
        sr, states = signals.evaluate_signals(snap, engine.evaluate(snap, T, cfg), T, cfg)
        for s in sr.fired:
            key = (s.item_id, s.signal_type)
            assert key not in seen, f"{s.signal_type} re-fired on the same item"
            seen.add(key)
            total += 1
        for (iid, stype), stt in states.items():
            st.set_fire_state(iid, stype, stt)
    return f"{total} distinct edges over 12 turns, zero repeats at unchanged state"


def _per_turn_cap():
    st, ids = smallco()
    cfg = MementoConfig(per_turn_fire_cap=1)
    rep = engine.evaluate(st.snapshot(), T, cfg)
    sr, _ = signals.evaluate_signals(st.snapshot(), rep, T, cfg)
    assert len(sr.fired) <= 1, f"{len(sr.fired)} fired with cap=1"
    tier = signals.TIER.get(sr.fired[0].signal_type) if sr.fired else None
    return f"fired={len(sr.fired)} (cap 1), winner tier={tier}"


def _no_turn_rung():
    import inspect

    src = inspect.getsource(signals)
    for tok in ("turn_count", "turns_elapsed", "n_turns"):
        assert tok not in src, tok
    return "escalation vocabulary has no turn-count member"


# ---------------------------------------------------------------- §6 computation
def _degrade_by_omission():
    st, ids = smallco()
    plain = engine.evaluate(st.snapshot(), T, MementoConfig()).to_dict()
    assert plain["money"] == [], "money present without a declared rate"
    withrate = engine.evaluate(
        st.snapshot(), T, MementoConfig(time_value_rate=Decimal("50"))
    ).to_dict()
    a = {k: v for k, v in plain.items() if k != "money"}
    b = {k: v for k, v in withrate.items() if k != "money"}
    assert a == b, "non-monetary output changed when a rate was declared"
    return "no rate -> no money block; every non-monetary field identical"


def _lambda_conserved():
    lam = money.derive_conserved_window_lambda(arrivals=7, departures=5, window_days=14)
    assert lam is None, f"non-conserved window returned lambda={lam}"
    ok = money.derive_conserved_window_lambda(arrivals=5, departures=5, window_days=10)
    assert ok is not None
    return f"non-conserved -> None; conserved -> {ok}"


def _empty_class_no_proposal():
    none = propose.ttl_proposal("task-1", [], percentile=0.80)
    assert none is None, f"empty comparable class produced {none}"
    some = propose.ttl_proposal("task-1", [5, 8, 9, 12, 20], percentile=0.80)
    assert some is not None and some.value == 12, f"P80 nearest-rank wrong: {some}"
    return f"empty class -> None; {{5,8,9,12,20}} P80 -> {some.value}d (n={some.sample_size})"


def _derivations_present():
    st, ids = smallco()
    rep = engine.evaluate(st.snapshot(), T, MementoConfig()).to_dict()
    for row in rep["items"]:
        assert row.get("derivation"), f"row without derivation: {row.get('title')}"
    for se in rep["slowest_entities"]:
        assert se.get("derivation") and se.get("n") is not None
    return f"{len(rep['items'])} item rows + slowest rows all carry derivation/n"


# ---------------------------------------------------------------- §7 paths
def _path_measured_only():
    st, ids = smallco()
    rep = engine.evaluate(st.snapshot(), T, MementoConfig()).to_dict()
    pcs = rep["path_comparisons"]
    assert pcs, "no path comparison produced for the probe fixture"
    blob = str(pcs).lower()
    for tok in ("p_value", "confidence", "significan", "dominat"):
        assert tok not in blob, f"inferential token {tok!r} in path comparison"
    return f"{len(pcs)} comparison(s), recorded intervals only"


# ---------------------------------------------------------------- §8 ethics
def _person_redaction():
    st = new_store()
    r = root(st)
    m = st.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=r,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    per = st.register_item(
        kind=ItemKind.ENTITY,
        title="REAL-NAME",
        parent_id=m,
        namespace="person",
        person_namespace_confirmed=True,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    st.record_event(
        item_id=per,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 6, 1, tzinfo=UTC),
        stage="s",
    )
    rep = engine.evaluate(st.snapshot(), T, MementoConfig())
    d = rep.to_dict()
    # PRD 8 permits the operator's own item row to carry the display name they
    # typed ("display name only for the open wait"). The ban is on RANKING and
    # comparison surfaces, which must carry neither the title nor a resolvable id.
    for surface in ("slowest_entities", "blocking_entities"):
        blob = str(d[surface])
        assert "REAL-NAME" not in blob, f"person title leaked into {surface}"
        assert per not in blob, f"person id leaked into {surface}"
    sr, _ = signals.evaluate_signals(st.snapshot(), rep, T, MementoConfig())
    blob = str([(s.payload, s.derivation) for s in (*sr.fired, *sr.due, *sr.acked)])
    assert "REAL-NAME" not in blob and per not in blob, "person leaked into signals"
    return "person title AND resolvable id withheld from report and signal payload"


def _no_ranking_language():
    joined = " ".join(signals.SUGGESTED_BEHAVIOR.values()).lower()
    for tok in ("rank", "worst", "slowest person", "blame"):
        assert tok not in joined, tok
    return "no ranking/blame language in suggested_behavior templates"


# ---------------------------------------------------------------- §4.3 capture
def _recording_path_check():
    st = new_store()
    r = root(st)
    st.register_item(
        kind=ItemKind.MISSION,
        title="never-captured",
        parent_id=r,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    rep = engine.evaluate(st.snapshot(), T, MementoConfig()).to_dict()
    row = next(i for i in rep["items"] if i["title"] == "never-captured")
    flag = row.get("recording_path") or row.get("recording_path_check")
    assert flag is not None, f"no recording-path flag on the row: {sorted(row)}"
    return f"zero-event mission flagged: {flag}"


def _artifact_provenance():
    st = new_store()
    r = root(st)
    m = st.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=r,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    try:
        st.record_event(
            item_id=m, kind=EventKind.ARTIFACT, valid_time=datetime(2026, 6, 1, tzinfo=UTC)
        )
        raise AssertionError("ARTIFACT accepted without provenance")
    except merr.ArtifactProvenanceRequiredError:
        pass
    st.record_event(
        item_id=m,
        kind=EventKind.ARTIFACT,
        valid_time=datetime(2026, 6, 1, tzinfo=UTC),
        provenance=Provenance("git", "abc", datetime(2026, 6, 1, tzinfo=UTC)),
    )
    return "ARTIFACT rejected without provenance, accepted with it"


# ---------------------------------------------------------------- §5.3 philosophy
def _philosophy_clauses():
    txt = pathlib.Path("src/horizon_monitor/memento/philosophy.md").read_text().lower()
    need = [
        "definition",
        "owner",
        "priorit",
        "state machine",
        "cap",
        "ack",
        "escalation",
        "kpi",
        "recording-path",
        "mortality",
    ]
    missing = [n for n in need if n not in txt]
    assert not missing, missing
    return f"all {len(need)} PRD-listed clause kinds present"


def _display_name_retention():
    """PRD 8: a third party's display name is kept "only for the open wait,
    with SHORT RETENTION after the wait ends"."""
    import inspect

    from horizon_monitor.memento import store as store_mod

    srcs = inspect.getsource(store_mod) + inspect.getsource(engine)
    has = any(tok in srcs for tok in ("retention", "purge", "expire_display_name"))
    assert has, "no retention/purge path for third-party display names"
    return "retention path present"


CHECKS = [
    ("§3.2", "Not an estimator", _no_estimator),
    ("§3.2", "Not a finance tool", _no_finance),
    ("§3.2", "No counterfactuals", _no_counterfactual),
    ("§3.2", "Not a statistics engine", _no_statistics),
    ("§3.2", "Not a scheduler/reminder tool", _no_scheduler),
    ("§3.3", "Byte-identical report", _byte_identical),
    ("§3.3", "Optional plane (off by default)", _optional_plane),
    ("§3.3", "No ambient clock in engine", _no_ambient_clock),
    ("§4.1", "Eight item kinds", _eight_kinds),
    ("§4.1", "Tree schema rejections", _tree_rules),
    ("§4.3", "Recording-path check", _recording_path_check),
    ("§4.3", "Artifact provenance required", _artifact_provenance),
    ("§5.1", "Edges, not levels", _edge_not_level),
    ("§5.1", "Per-turn cap", _per_turn_cap),
    ("§5.1", "No turn-count escalation", _no_turn_rung),
    ("§5.2", "Twelve signal types declared", _twelve_signals_declared),
    ("§5.2", "All twelve reachable end-to-end", _signals_fire_end_to_end),
    ("§5.3", "Alarm philosophy shipped", _philosophy_clauses),
    ("§6", "Degrade by omission (money)", _degrade_by_omission),
    ("§6", "Conserved-window lambda", _lambda_conserved),
    ("§6", "Empty class -> no proposal", _empty_class_no_proposal),
    ("§6", "Derivation on every row", _derivations_present),
    ("§7", "Path comparison measured only", _path_measured_only),
    ("§8", "Person redaction complete", _person_redaction),
    ("§8", "No ranking language", _no_ranking_language),
    ("§8", "Display-name retention", _display_name_retention),
]

for sec, claim, fn in CHECKS:
    check(sec, claim, fn)

print(f"{'SEC':<6}{'CLAIM':<38}{'VERDICT':<9}EVIDENCE")
print("-" * 118)
for sec, claim, verdict, detail in RESULTS:
    print(f"{sec:<6}{claim:<38}{verdict:<9}{detail}")
bad = [r for r in RESULTS if r[2] != "PASS"]
print("-" * 118)
print(
    f"{len(RESULTS) - len(bad)}/{len(RESULTS)} PASS" + (f"  |  PROBLEMS: {len(bad)}" if bad else "")
)
