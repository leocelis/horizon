"""Shared helpers for the V1/V2/V3/V5 validation gates.

Datasets are loaded from the directory referenced by the
``HORIZON_VALIDATION_DATA`` environment variable. When unset, every validation
test is skipped with a clear explanation — the tests are shipped in the repo
so the gate logic is reviewable, but they only execute when real labeled data
is supplied.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import pytest


def dataset_dir() -> Path | None:
    """Return the validation-data directory if configured, else None."""
    env = os.environ.get("HORIZON_VALIDATION_DATA")
    if not env:
        return None
    path = Path(env).expanduser()
    return path if path.exists() else None


def require_dataset(filename: str) -> Path:
    """Skip the test when the dataset file is not available."""
    root = dataset_dir()
    if root is None:
        pytest.skip(
            "HORIZON_VALIDATION_DATA not set — validation gates need labeled data "
            "(see tests/validation/README.md)."
        )
    target = root / filename
    if not target.exists():
        pytest.skip(f"Validation dataset missing: {target}")
    return target


def load_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
