"""Oracle for cluster_points_m, ported verbatim from the Step 0 grader."""


def _same(labels, i, j):
    return labels[i] == labels[j]


def build_checks(f):
    def control():
        # ~300 m pair at the equator plus a point ~10 km away.
        labels = list(f([(0, 0), (0.0027, 0), (0.09, 0)], 500))
        ok = _same(labels, 0, 1) and not _same(labels, 0, 2)
        return ok, f"labels {labels}"

    def high_lat():
        # 0.012 deg of longitude at 75N is ~346 m — within 500 m.
        # A degrees-converted eps (500/111320) calls them separate.
        labels = list(f([(0, 75), (0.012, 75)], 500))
        return _same(labels, 0, 1), f"labels {labels} (points are ~346 m apart)"

    def dateline():
        labels = list(f([(179.999, 0), (-179.999, 0)], 500))
        return _same(labels, 0, 1), f"labels {labels} (points are ~222 m apart)"

    return [
        ("300m_pair_plus_outlier", "control", control),
        ("east_west_at_75N", "edge", high_lat),
        ("pair_across_dateline", "edge", dateline),
    ]
