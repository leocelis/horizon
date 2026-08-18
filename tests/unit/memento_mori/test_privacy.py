"""Parent constraint: local_first_privacy.

horizon_memento_mori_intent.yaml::constraints[local_first_privacy].
test: tests/unit/memento_mori/test_privacy.py::test_no_external_calls_and_no_bundled_data
"""

from __future__ import annotations

import socket
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from horizon_monitor.memento import engine
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


class _OutboundNetworkError(AssertionError):
    pass


def _block_outbound(*args, **kwargs):
    raise _OutboundNetworkError(f"unexpected outbound network call: args={args} kwargs={kwargs}")


def test_no_external_calls_and_no_bundled_data(tmp_path: Path) -> None:
    """The mission store is a local file at an operator-configured path;
    default configuration sends zero mission data externally; the engine
    ships with no bundled mission data of any kind."""
    db_path = tmp_path / "memento.db"
    assert not db_path.exists(), "the store must not exist until the operator configures a path"

    store = MementoStore(db_path)
    assert db_path.exists(), "the store must be a local file at the configured path"

    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    store.register_item(
        kind=ItemKind.MISSION,
        title="a private mission",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )

    with patch.object(socket.socket, "connect", side_effect=_block_outbound):
        with patch.object(socket.socket, "connect_ex", side_effect=_block_outbound):
            snapshot = store.snapshot()
            report = engine.evaluate(snapshot, datetime(2026, 8, 18, tzinfo=UTC), MementoConfig())

    assert report is not None
    store.close()

    # No bundled mission data ships with the package: the memento package's
    # source tree contains no seeded item/mission records.
    import horizon_monitor.memento as memento_pkg

    package_dir = Path(memento_pkg.__file__).parent
    for py_file in package_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        assert "ship-widget" not in text, f"{py_file} bundles fixture/example mission data"
