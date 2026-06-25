"""Regression guard for the red-team remediation (Fix 1 + Fix 2).

These assert that the retracted over-claims do not creep back into the
*user-facing* surfaces (README + landing pages + LEGAL), and that the required
honest framing is present. Internal research/PRD docs may still *discuss* the
retracted framing under their clearly-marked background banners, so broad bans
there would be too strict — instead we guard the PRD executive sections that
must align with Fix 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# User-facing surfaces that must stay free of impossibility / "blind" over-claims.
USER_FACING = [
    ROOT / "README.md",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "site" / "index.html",
]

# Substrings that must NOT appear (case-insensitive) on user-facing surfaces.
BANNED = [
    "architecturally blind",
    "no-go theorem",
    "no go theorem",
    "prove why no llm can self-monitor",
    "cannot fully self-monitor",
    "by mathematical proof",
    "mathematical impossibility",
]

# LEGAL may mention no-go results in a retracted/motivation-only context — ban strong claims only.
LEGAL_BANNED = [
    "architecturally blind",
    "three no-go theorems prove",
    "prove why no llm can self-monitor",
    "cannot fully self-monitor",
    "by mathematical proof",
    "mathematical impossibility",
    "cites 173 academic references and three no-go theorems",
]

PRD = ROOT / "docs" / "product" / "THCP_FIDELITY_MONITOR_PRD.md"

CONTENT_MARKETING = [
    ROOT / "docs" / "content" / "naming-the-category-conversation-dynamics-monitoring.md",
    ROOT / "docs" / "content" / "why-every-production-agent-needs-conversation-dynamics-monitoring.md",
]


@pytest.mark.parametrize("path", USER_FACING, ids=lambda p: p.name)
def test_no_impossibility_overclaims(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    hits = [phrase for phrase in BANNED if phrase in text]
    assert not hits, f"{path.name} still contains retracted over-claim(s): {hits}"


def test_legal_no_impossibility_overclaims() -> None:
    text = (ROOT / "LEGAL.md").read_text(encoding="utf-8").lower()
    hits = [phrase for phrase in LEGAL_BANNED if phrase in text]
    assert not hits, f"LEGAL.md still contains retracted over-claim(s): {hits}"


def test_legal_has_empirical_framing() -> None:
    text = (ROOT / "LEGAL.md").read_text(encoding="utf-8").lower()
    assert "background motivation" in text
    assert "not as mathematical proof" in text
    assert "limited and unreliable" in text or "do not reliably" in text
    assert "empirical" in text


def test_prd_computation_model_empirical_framing() -> None:
    """§4.4 must cite trilemma as design inspiration, not impossibility proof."""
    text = PRD.read_text(encoding="utf-8")
    section_start = text.index("### 4.4 Computation Model")
    section_end = text.index("**Computation map:**", section_start)
    section = text[section_start:section_end]
    lower = section.lower()
    assert "design inspiration" in lower
    assert "not a proof that self-monitoring is impossible" in lower
    assert "mathematical impossibility" not in lower


def test_prd_executive_no_impossibility_proof() -> None:
    """§3 competitive check must not rest on IPM as proof (Fix 1)."""
    text = PRD.read_text(encoding="utf-8")
    section_start = text.index("**Why won't models solve this themselves?**")
    section_end = text.index("## 4. Product Vision", section_start)
    section = text[section_start:section_end].lower()
    assert "not an impossibility proof" in section
    assert "design inspiration" in section
    assert "three lines of evidence close this path" not in section


def test_prd_appendix_e_conclusion_empirical_framing() -> None:
    """Appendix E closing paragraph must not rest on impossibility."""
    text = PRD.read_text(encoding="utf-8")
    section_start = text.index("### E.5 The Physics Parallel Is Not Decorative")
    section = text[section_start:]
    lower = section.lower()
    assert "mathematical impossibility" not in lower
    assert "do not *reliably* surface" in lower or "do not reliably surface" in lower


def test_readme_has_empirical_and_metaphor_framing() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    # Fix 1: empirical necessity framing.
    assert "do not reliably surface" in text
    # Fix 3 positioning: observability-first.
    assert "observability first" in text
    # Fix 2: physics labelled as metaphor.
    assert "metaphor" in text
    # The +15.7% must not stand unqualified — a caveat word appears near it.
    assert "synthetic" in text


def test_interval_docstring_labels_metaphor() -> None:
    """The spacetime interval source must flag itself as metaphor + metadata-only."""
    text = (
        (ROOT / "src" / "horizon" / "spacetime" / "interval.py").read_text(encoding="utf-8").lower()
    )
    assert "metaphor" in text
    assert "metadata only" in text


def test_light_cone_docstring_labels_metaphor() -> None:
    text = (
        (ROOT / "src" / "horizon" / "spacetime" / "light_cone.py")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "metaphor" in text


@pytest.mark.parametrize("path", CONTENT_MARKETING, ids=lambda p: p.name)
def test_content_marketing_caveats_performance_claims(path: Path) -> None:
    """Long-form content must not present +15.7% as production evidence."""
    text = path.read_text(encoding="utf-8").lower()
    if "+15.7%" not in text:
        pytest.skip("no +15.7% claim in this doc")
    assert "synthetic" in text
    assert "observability" in text or "production" in text or "lab" in text
