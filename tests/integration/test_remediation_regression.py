"""Regression tests for the red-team remediation (Fix 1–4 tooling + artifacts).

Exercises the added analysis library, validation scripts, committed evidence
JSON, and repo hygiene so regressions are caught in CI without slow OOD runs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
REVIEWS = ROOT / "docs" / "reviews"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ── analysis public API ───────────────────────────────────────────────────────


def test_analysis_package_exports() -> None:
    import horizon.analysis as analysis

    for name in (
        "analyze_leading_indicator",
        "analyze_session_leading_indicator",
        "run_interventional_ab",
        "sign_test",
        "DEFAULT_ACTIONABLE",
        "OUTCOME_METRIC",
        "EventLeadStats",
        "LeadingIndicatorReport",
    ):
        assert hasattr(analysis, name), f"missing export: {name}"


# ── CLI scripts (Fix 3) ───────────────────────────────────────────────────────


def test_measure_leading_indicator_demo_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mli = _load_script("measure_leading_indicator")
    out = tmp_path / "leading_demo.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "measure_leading_indicator.py",
            "--demo",
            "--out",
            str(out),
            "--min-samples",
            "2",
        ],
    )
    assert mli.main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source"] == "synthetic-demo"
    assert "caveat" in data
    assert data["n_conversations"] >= 1
    assert data["n_turns_total"] > 0
    assert "per_event" in data
    assert "synthetic" in data["caveat"].lower()


def test_run_interventional_ab_demo_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ab = _load_script("run_interventional_ab")
    out = tmp_path / "ab_demo.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_interventional_ab.py", "--demo", "--out", str(out)],
    )
    assert ab.main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source"] == "synthetic-demo"
    assert "caveat" in data
    assert "ada" not in data["caveat"].lower()
    assert data["n_conversations"] >= 1
    assert data["n_turns"] >= 1
    assert -1.0 <= data["mean_control_outcome"] <= 1.0
    assert -1.0 <= data["mean_treatment_outcome"] <= 1.0
    assert set(data["sign_test"]) == {"wins", "losses", "p_value"}


def test_interventional_ab_demo_reproduces_committed_artifact() -> None:
    """Demo CLI must match the checked-in evidence artifact (deterministic demo)."""
    committed = json.loads((REVIEWS / "interventional_ab_demo.json").read_text(encoding="utf-8"))
    from horizon.analysis.interventional_ab import DEFAULT_ACTIONABLE, run_interventional_ab

    ab_mod = _load_script("run_interventional_ab")
    result = run_interventional_ab(ab_mod._demo_conversations(), set(DEFAULT_ACTIONABLE))
    for key in (
        "n_conversations",
        "n_turns",
        "mean_control_outcome",
        "mean_treatment_outcome",
        "absolute_lift",
        "relative_lift",
    ):
        assert result[key] == committed[key], key


# ── committed evidence JSON ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    ["interventional_ab_demo.json", "leading_indicator.json"],
)
def test_committed_evidence_artifacts(name: str) -> None:
    data = json.loads((REVIEWS / name).read_text(encoding="utf-8"))
    assert "caveat" in data
    caveat = data["caveat"].lower()
    assert any(
        word in caveat
        for word in ("production", "synthetic", "intervention", "corpus")
    )


def test_leading_indicator_artifact_shape() -> None:
    data = json.loads((REVIEWS / "leading_indicator.json").read_text(encoding="utf-8"))
    assert data["source"]
    assert "per_event" in data
    assert data["horizon_k"] >= 1
    assert data["n_trajectories"] >= 1


# ── repo hygiene ──────────────────────────────────────────────────────────────


def test_no_private_directory_at_repo_root() -> None:
    """Private docs must not live in the OSS repo tree."""
    assert not (ROOT / "_private").is_dir()
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "_private/" not in gitignore


def test_requirements_dev_has_ml_pins() -> None:
    text = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "sentence-transformers" in text
    assert "pyarrow" in text


# ── landing / social preview (Fix 1 + honest claims) ─────────────────────────


@pytest.mark.parametrize(
    "path",
    [ROOT / "docs" / "index.html", ROOT / "docs" / "site" / "index.html"],
    ids=["docs-index", "site-index"],
)
def test_landing_og_meta_no_uncaveated_lift(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    og_start = text.index('property="og:description"')
    og_chunk = text[og_start : og_start + 400]
    assert "+15.7%" not in og_chunk
    assert "observability" in og_chunk or "multi-turn" in og_chunk


@pytest.mark.parametrize(
    "path",
    [ROOT / "docs" / "index.html", ROOT / "docs" / "site" / "index.html"],
    ids=["docs-index", "site-index"],
)
def test_landing_stats_label_synthetic(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    assert "synthetic a/b" in text
