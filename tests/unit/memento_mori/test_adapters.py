"""G-12 — GitLocalAdapter emits ARTIFACT-ready records with full provenance;
the adapter interface cannot create a mission link (API has no such
parameter) (MEMENTO_MORI_TECH_SPEC.md §6, §7)."""

from __future__ import annotations

import inspect
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from horizon_monitor.memento.adapters.base import ArtifactAdapter, RawArtifact
from horizon_monitor.memento.adapters.git_local import GitLocalAdapter
from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def _init_repo_with_one_commit(repo_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo_path)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "config", "user.email", "test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repo_path), "config", "user.name", "Test"], check=True)
    (repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_path), "add", "README.md"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-q", "-m", "initial commit"], check=True
    )


def test_git_local_adapter_emits_full_provenance(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_repo_with_one_commit(repo_path)

    adapter = GitLocalAdapter(repo_path=str(repo_path))
    artifacts = adapter.pull(since=None)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert isinstance(artifact, RawArtifact)
    assert artifact.provenance.source_system == "git_local"
    assert artifact.provenance.native_id  # the commit sha
    assert isinstance(artifact.provenance.raw_timestamp, datetime)
    assert artifact.payload["subject"] == "initial commit"


def test_git_local_adapter_returns_empty_tuple_for_nonexistent_repo(tmp_path: Path) -> None:
    """Must not raise on a bad source — an empty tuple, per the
    ArtifactAdapter contract."""
    adapter = GitLocalAdapter(repo_path=str(tmp_path / "does-not-exist"))
    assert adapter.pull(since=None) == ()


def test_adapter_interface_has_no_link_creating_parameter() -> None:
    """G-12: "adapter cannot create links (API has no such parameter)" — a
    structural, not just behavioral, guarantee: inspect the interface's own
    signature."""
    pull_signature = inspect.signature(ArtifactAdapter.pull)
    param_names = set(pull_signature.parameters) - {"self"}
    assert param_names == {"since"}
    for banned in ("item_id", "mission_id", "link", "parent_id"):
        assert banned not in param_names

    git_local_signature = inspect.signature(GitLocalAdapter.pull)
    git_local_param_names = set(git_local_signature.parameters) - {"self"}
    assert git_local_param_names == {"since"}


def test_caller_links_a_pulled_artifact_only_through_the_validated_write_path(
    store: MementoStore, tmp_path: Path
) -> None:
    """The adapter hands back a provenance-carrying RawArtifact with no
    item_id anywhere on it; only the caller, writing through
    MementoStore.record_event with an explicit item_id, creates the link to
    a mission — exactly the "clock_register association" the tech spec
    describes."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_repo_with_one_commit(repo_path)
    artifact = GitLocalAdapter(repo_path=str(repo_path)).pull(since=None)[0]

    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )

    event_id = store.record_event(
        item_id=mission_id,  # the caller's explicit choice — never the adapter's
        kind=EventKind.ARTIFACT,
        valid_time=artifact.provenance.raw_timestamp,
        provenance=artifact.provenance,
    )
    events = store.get_events(mission_id)
    assert any(e.event_id == event_id and e.provenance == artifact.provenance for e in events)
