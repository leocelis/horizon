"""Single source of truth for the mission store's schema version.

Defined once, imported by every backend and by the store, so a bump cannot be
applied to one dialect and forgotten in another — the divergence would be
invisible until a store migrated under one backend refused to open under the
other.
"""

SCHEMA_VERSION = "2"
