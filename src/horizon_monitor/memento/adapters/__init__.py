"""Pull-based artifact adapters (MEMENTO_MORI_TECH_SPEC.md §6, §7).

An adapter translates one external append-only source into provenance-
carrying :class:`~horizon_monitor.memento.adapters.base.RawArtifact` records.
Adapters never write links: there is no ``item_id`` / ``mission_id`` /
``link`` parameter anywhere on the interface. Linking an artifact stream to
a mission is always an explicit, separate ``clock_register``-path decision
made by the caller (test plan G-12).
"""

from horizon_monitor.memento.adapters.base import ArtifactAdapter, RawArtifact
from horizon_monitor.memento.adapters.git_local import GitLocalAdapter

__all__ = ["ArtifactAdapter", "RawArtifact", "GitLocalAdapter"]
