"""ArtifactAdapter interface — pull-based, provenance-carrying, link-free.

Per MEMENTO_MORI_TECH_SPEC.md §6: "Artifact adapters... pull-based readers
that translate an external append-only source into ARTIFACT events with
mandatory provenance... adapters never write links — linking an artifact
stream to a mission is a caller ``clock_register`` association."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from horizon_monitor.memento.models import Provenance


@dataclass(frozen=True)
class RawArtifact:
    """One record pulled from an external append-only source, before any
    mission link exists.

    This is deliberately not a :class:`~horizon_monitor.memento.models.ClockEvent`:
    a ``ClockEvent`` requires an ``item_id``, and no field here provides one.
    The caller decides, through the normal validated write path, which item
    (if any) a given raw artifact belongs to — the adapter itself has no
    opinion and no capability to record one (test plan G-12: "adapter cannot
    create links (API has no such parameter)").
    """

    provenance: Provenance
    payload: dict


class ArtifactAdapter(Protocol):
    """Pull-based reader over one external append-only source.

    Implementations read from git, an issue tracker, a mail store, etc. and
    return :class:`RawArtifact` records with full provenance
    (``source_system``, ``native_id``, ``raw_timestamp``). The interface has
    no method or parameter capable of attaching an item_id or mission_id —
    by construction, an adapter cannot create a link.
    """

    def pull(self, since: datetime | None) -> tuple[RawArtifact, ...]:
        """Return every record newly available since ``since`` (``None``
        means: return all available history). Must return an empty tuple
        rather than raise when the source has nothing new."""
        ...
