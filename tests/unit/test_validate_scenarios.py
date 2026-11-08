"""Every `horizon-validate` scenario passes.

The README tells new users to run `horizon-validate` to verify an install. From
v0.2.0 to v0.3.1 it reported "1/5 scenarios failed" on every install: the
convergent scenario set only convergence_threshold, which v0.2.0 narrowed to the
IGT slope, while the absolute check moved to convergence_igt_ceiling. Nothing
ran the harness in CI, so the failure was invisible.
"""

from __future__ import annotations

import pytest

from horizon_monitor import FidelityMonitor
from horizon_monitor.validate import SCENARIOS


@pytest.mark.parametrize(("name", "scenario"), SCENARIOS, ids=[n for n, _ in SCENARIOS])
def test_validate_scenario_passes(name, scenario) -> None:
    checks = scenario(FidelityMonitor())
    failed = [f"{label}: {detail}" for label, ok, detail in checks if not ok]
    assert not failed, f"{name}: {failed}"


def test_harness_runs_five_scenarios() -> None:
    assert len(SCENARIOS) == 5
