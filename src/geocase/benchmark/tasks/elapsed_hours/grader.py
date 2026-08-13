"""Oracle for elapsed_hours: the DST transition.

Subtracting two naive ``fromisoformat`` values ignores the zone entirely and
reports 24.0 hours across the night the clocks go back, when 25 hours actually
elapsed. Both controls — same day, and a day with no transition — are invariant
under the defect, so an implementation that never localises passes them.
"""

TOL = 1e-9


def _close(got, exp):
    return (
        isinstance(got, (int, float))
        and not isinstance(got, bool)
        and abs(got - exp) <= TOL
    )


def build_checks(f):
    def same_day():
        got = f("2026-03-01T09:30:00", "2026-03-01T12:00:00", "America/New_York")
        return _close(got, 2.5), f"got {got!r}, expected 2.5"

    def plain_day():
        got = f("2026-06-10T00:00:00", "2026-06-11T00:00:00", "America/New_York")
        return _close(got, 24.0), f"got {got!r}, expected 24.0"

    def dst_fall_back():
        # US clocks go back on 2026-11-01, so this local midnight-to-midnight
        # span is 25 hours long.
        got = f("2026-11-01T00:00:00", "2026-11-02T00:00:00", "America/New_York")
        return _close(got, 25.0), f"got {got!r}, expected 25.0"

    return [
        ("same_day", "control", same_day),
        ("plain_day", "control", plain_day),
        ("dst_fall_back", "edge", dst_fall_back),
    ]
