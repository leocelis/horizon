"""Clock enums must compare equal to their values on every supported Python.

Python 3.10 has no enum.StrEnum. A str mixin is the stand-in. These assertions
fail if a member stops being the string the store writes.
"""

from horizon_monitor.memento.models import EventKind, ItemKind, SignalState


def test_clock_enums_compare_equal_to_their_string_values() -> None:
    assert ItemKind.HORIZON == "horizon"
    assert str(ItemKind.HORIZON) == "horizon"
    assert EventKind.PROGRESS == "progress"
    assert SignalState.CLEAR == "clear"
