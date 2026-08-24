"""Artifact ingestion — the bridge from an adapter's raw records to the store.

This is the layer the research calls for and the adapters deliberately cannot
provide themselves. `ArtifactAdapter` has no method or parameter capable of
attaching an item — by construction it cannot invent a link. Ingestion is where
a *caller* supplies one, explicitly, through the normal validated write path.

Why it matters (PRD §4.3): the plane is usable only if most timestamps are a
side-effect of work that already happened. Manual reconstruction dies —
self-tracking abandons at the point of collection cost, and professional
timesheets are structurally biased. Deriving events from append-only sources a
team already produces is the only capture strategy that survives without a new
habit; an agent that must *remember* to record is worth nothing on the day it
forgets.

The split this module preserves:

* **Derived automatically** — that something was created, moved, or touched,
  with the source's own provenance (source system, native id, raw timestamp).
* **Written by a caller** — which mission it belongs to. Never inferred here,
  never guessed by a model. `item_id` is a required argument with no default.

Ingestion is deliberately **not** an MCP tool. It is operator- or
scheduler-invoked (see `scripts/ingest_artifacts.py`), because "subscribe to a
source" is a standing arrangement, not a conversational act.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from horizon_monitor.memento.models import EventKind

__all__ = ["IngestResult", "ingest_artifacts"]


@dataclass(frozen=True)
class IngestResult:
    """What one ingestion run did — reported, never merely performed."""

    source_system: str
    ingested: int
    skipped_duplicates: int
    latest_valid_time: datetime | None
    pulled: int

    def summary(self) -> str:
        newest = self.latest_valid_time.isoformat() if self.latest_valid_time else "none"
        return (
            f"{self.source_system}: pulled {self.pulled}, ingested {self.ingested}, "
            f"skipped {self.skipped_duplicates} already-recorded; newest {newest}"
        )


def ingest_artifacts(store, adapter, *, item_id: str, since: datetime | None = None):
    """Pull from `adapter` and record each new artifact against `item_id`.

    `item_id` is required and has no default: it is the caller-supplied link,
    the one fact an append-only source structurally cannot know.

    Idempotent. `since` defaults to the newest artifact already recorded from
    this source, so a repeat run asks the source only for what is new; anything
    that arrives twice anyway is dropped by native-id dedupe. Running this on a
    schedule is therefore safe, which is the point — a capture path that is
    unsafe to re-run will not be automated, and one that is not automated
    depends on somebody remembering.

    Artifacts are written with `EventKind.ARTIFACT`, whose provenance
    requirement the store enforces: an artifact event without a complete
    provenance triple is rejected before anything is written.
    """
    source_hint = getattr(adapter, "source_system", None)
    if since is None and source_hint:
        since = store.latest_artifact_time(source_hint)
    raw = adapter.pull(since)

    if not raw:
        source = source_hint or "unknown"
        return IngestResult(source, 0, 0, store.latest_artifact_time(source), 0)

    source = raw[0].provenance.source_system
    known = store.known_artifact_ids(source)

    ingested = skipped = 0
    newest: datetime | None = None
    for art in raw:
        native_id = art.provenance.native_id
        if native_id in known:
            skipped += 1
            continue
        store.record_event(
            item_id=item_id,
            kind=EventKind.ARTIFACT,
            valid_time=art.provenance.raw_timestamp,
            provenance=art.provenance,
            payload=art.payload,
        )
        ingested += 1
        if newest is None or art.provenance.raw_timestamp > newest:
            newest = art.provenance.raw_timestamp

    return IngestResult(
        source_system=source,
        ingested=ingested,
        skipped_duplicates=skipped,
        latest_valid_time=store.latest_artifact_time(source),
        pulled=len(raw),
    )
