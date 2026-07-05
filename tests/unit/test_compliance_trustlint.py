"""TrustLint / ComplyEdge compliance gate for Horizon LLM-facing artifacts."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = ROOT / "scripts" / "compliance" / "check.sh"
RECIPE = ROOT / "recipes" / "compliance-trustlint.yaml"
CURSOR_RULE = ROOT / "docs" / "cursor-rules" / "horizon-monitor.mdc"


def _resolve_rules_dir() -> Path:
    cache = ROOT / ".trustlint-cache" / "rules"
    if cache.exists() and any(cache.rglob("*.yaml")):
        return cache
    home = Path.home() / ".trustlint" / "rules"
    if home.exists() and any(home.rglob("*.yaml")):
        return home
    raise FileNotFoundError("TrustLint rules not bootstrapped — run ./scripts/compliance/check.sh")


@pytest.fixture(scope="session", autouse=True)
def _ensure_trustlint_rules() -> None:
    try:
        _resolve_rules_dir()
    except FileNotFoundError:
        subprocess.run(["bash", str(CHECK_SCRIPT)], cwd=str(ROOT), check=True, timeout=300)


class TestComplianceRecipe:
    def test_recipe_exists_with_fences(self) -> None:
        assert RECIPE.is_file()
        text = RECIPE.read_text(encoding="utf-8")
        assert "<BEGIN-COMPLYEDGE v1.0>" in text
        assert "<END-COMPLYEDGE v1.0>" in text
        assert "scripts/compliance/check.sh" in text

    def test_repo_has_trustlint_config(self) -> None:
        cfg = ROOT / ".trustlint.yaml"
        assert cfg.is_file()
        text = cfg.read_text(encoding="utf-8")
        assert "jurisdiction: EU" in text
        assert "docs/spec/**/*_intent.yaml" in text
        assert "docs/cursor-rules/**/*.mdc" in text


class TestComplianceCheckScript:
    def test_check_script_exists(self) -> None:
        assert CHECK_SCRIPT.is_file()

    @pytest.mark.skipif(
        subprocess.run(["which", "trustlint"], capture_output=True).returncode != 0,
        reason="trustlint not installed",
    )
    def test_full_repo_scan_passes(self) -> None:
        proc = subprocess.run(
            ["bash", str(CHECK_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    @pytest.mark.skipif(
        subprocess.run(["which", "trustlint"], capture_output=True).returncode != 0,
        reason="trustlint not installed",
    )
    def test_detects_art5_violation(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad_intent.yaml"
        bad.write_text(
            "constraints:\n"
            "  - name: social_scoring\n"
            "    requirement: Deploy social credit score for all citizens\n",
            encoding="utf-8",
        )
        rules_dir = _resolve_rules_dir()
        proc = subprocess.run(
            ["trustlint", "--rules-dir", str(rules_dir), "check", str(bad), "-j", "EU"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1
        combined = (proc.stdout + proc.stderr).upper()
        assert "EU_AI_ACT" in combined or "SOCIAL" in combined


class TestComplyEdgeIntegration:
    def test_complyedge_integration_doc_exists(self) -> None:
        doc = ROOT / "docs" / "integrations" / "COMPLYEDGE.md"
        assert doc.is_file()
        text = doc.read_text(encoding="utf-8")
        assert "horizon" in text
        assert "runtime_check.sh" in text
        assert "trust.complyedge.io/horizon" in text
        assert "Customer #0" not in text
        assert "dogfood" not in text.lower()

    def test_runtime_check_script_exists(self) -> None:
        script = ROOT / "scripts" / "compliance" / "runtime_check.sh"
        assert script.is_file()

    def test_readme_live_badge_embed(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "api.complyedge.io/v1/public/badge/horizon.svg" in readme
        assert "trust.complyedge.io/horizon" in readme


class TestAgentRuleBlock:
    def test_cursor_rule_has_complyedge_block(self) -> None:
        text = CURSOR_RULE.read_text(encoding="utf-8")
        assert "<BEGIN-COMPLYEDGE v1.0>" in text
        assert "./scripts/compliance/check.sh" in text
