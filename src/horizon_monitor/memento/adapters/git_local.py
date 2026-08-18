"""Reference ArtifactAdapter: local git commit history.

Reads ``git log`` on a local repository path (no fetch, no remote, no
network call) and returns one :class:`RawArtifact` per commit with full
provenance. This is the shipped reference implementation of
:class:`~horizon_monitor.memento.adapters.base.ArtifactAdapter`
(MEMENTO_MORI_TECH_SPEC.md §7).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime

from horizon_monitor.memento.adapters.base import RawArtifact
from horizon_monitor.memento.models import Provenance

_FIELD_SEP = "\x1f"
_LOG_FORMAT = f"%H{_FIELD_SEP}%aI{_FIELD_SEP}%an{_FIELD_SEP}%s"


@dataclass(frozen=True)
class GitLocalAdapter:
    """Pull-based reader over ``git log`` for one local repository checkout.

    ``repo_path`` must already exist on disk; this adapter never clones,
    fetches, or otherwise reaches the network — it shells out to the local
    ``git`` binary against an already-checked-out working tree only.
    """

    repo_path: str
    source_system: str = "git_local"

    def pull(self, since: datetime | None) -> tuple[RawArtifact, ...]:
        """Return one RawArtifact per commit reachable from HEAD, newest
        first. ``since`` (if given) is passed to ``git log --since`` as an
        ISO-8601 timestamp; commits are the source's own append-only log —
        nothing here mutates the repository."""
        cmd = ["git", "-C", self.repo_path, "log", f"--pretty=format:{_LOG_FORMAT}"]
        if since is not None:
            cmd.append(f"--since={since.isoformat()}")

        try:
            result = subprocess.run(  # noqa: S603 — local git binary, fixed argv, no shell
                cmd, capture_output=True, text=True, check=True, timeout=30
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return ()

        artifacts: list[RawArtifact] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split(_FIELD_SEP)
            if len(parts) != 4:
                continue
            commit_sha, raw_timestamp, author, subject = parts
            artifacts.append(
                RawArtifact(
                    provenance=Provenance(
                        source_system=self.source_system,
                        native_id=commit_sha,
                        raw_timestamp=datetime.fromisoformat(raw_timestamp),
                    ),
                    payload={"author": author, "subject": subject},
                )
            )
        return tuple(artifacts)
