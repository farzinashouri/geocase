"""Oracle for segment_intersection (ALG-0028): collinear overlapping segments
must return the overlap segment — determinant-only solvers return None."""

TOL = 1e-9


def _is_point(v):
    return (
        isinstance(v, (tuple, list))
        and len(v) == 2
        and all(isinstance(c, (int, float)) for c in v)
    )


def _close(a, b):
    return abs(a[0] - b[0]) <= TOL and abs(a[1] - b[1]) <= TOL


def build_checks(f):
    def crossing():
        got = f(((0.0, 0.0), (4.0, 4.0)), ((0.0, 4.0), (4.0, 0.0)))
        ok = _is_point(got) and _close(got, (2.0, 2.0))
        return ok, f"got {got!r}, expected (2.0, 2.0)"

    def disjoint():
        got = f(((0.0, 0.0), (1.0, 0.0)), ((3.0, 1.0), (4.0, 1.0)))
        return got is None, f"got {got!r}, expected None"

    def collinear_overlap():
        got = f(((0.0, 0.0), (5.0, 0.0)), ((2.0, 0.0), (8.0, 0.0)))
        exp = ((2.0, 0.0), (5.0, 0.0))
        ok = (
            isinstance(got, (tuple, list))
            and len(got) == 2
            and all(_is_point(p) for p in got)
            and (
                (_close(got[0], exp[0]) and _close(got[1], exp[1]))
                or (_close(got[0], exp[1]) and _close(got[1], exp[0]))
            )
        )
        return ok, f"got {got!r}, expected the overlap segment ((2,0), (5,0))"

    return [
        ("crossing_segments", "control", crossing),
        ("disjoint_segments", "control", disjoint),
        ("collinear_overlap", "edge", collinear_overlap),
    ]
