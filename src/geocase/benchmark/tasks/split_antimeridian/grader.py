"""Oracle for split_antimeridian (FND-0047): a crossing polygon becomes two
parts, geodesic area is preserved, and no part spans more than 300 degrees of
longitude. The expected area comes from the unwrapped reference polygon."""

from shapely.geometry import Polygon, box

from geocase.benchmark._oracle_utils import GEOD, rel_ok


def _total_geodesic_area(parts):
    return sum(abs(GEOD.geometry_area_perimeter(p)[0]) for p in parts)


def _max_lon_span(parts):
    spans = []
    for p in parts:
        w, _, e, _ = p.bounds
        spans.append(e - w)
    return max(spans)


def build_checks(f):
    def control():
        poly = box(10, 10, 20, 20)
        got = f(poly)
        ok = len(got) == 1 and got[0].is_valid and got[0].equals(poly)
        return (
            ok,
            f"{len(got)} part(s), unchanged={len(got) == 1 and got[0].equals(poly)}",
        )

    def crossing():
        poly = Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1)])
        ref = Polygon([(179, 0), (181, 0), (181, 1), (179, 1)])
        exp_area = abs(GEOD.geometry_area_perimeter(ref)[0])
        got = list(f(poly))
        area = _total_geodesic_area(got)
        span = _max_lon_span(got)
        ok = (
            len(got) >= 2
            and all(p.is_valid for p in got)
            and span < 300
            and rel_ok(area, exp_area, 0.01)
        )
        return ok, (
            f"{len(got)} part(s), max lon span {span:.1f} deg, "
            f"area {area:.4g} (expected {exp_area:.4g})"
        )

    def battery(ring, ref_ring):
        def check():
            exp_area = abs(GEOD.geometry_area_perimeter(Polygon(ref_ring))[0])
            got = list(f(Polygon(ring)))
            area = _total_geodesic_area(got)
            span = _max_lon_span(got)
            ok = (
                len(got) >= 2
                and all(p.is_valid for p in got)
                and span < 300
                and rel_ok(area, exp_area, 0.02)
            )
            return ok, (
                f"{len(got)} part(s), max lon span {span:.1f} deg, "
                f"area {area:.4g} (expected {exp_area:.4g})"
            )

        return check

    return [
        ("non_crossing_passthrough", "control", control),
        ("crossing_box_two_parts", "edge", crossing),
        (
            "westward_ring",
            "edge",
            battery(
                [(-175, -20), (175, -20), (175, -15), (-175, -15)],
                [(-175, -20), (-185, -20), (-185, -15), (-175, -15)],
            ),
        ),
        (
            "pole_adjacent",
            "edge",
            battery(
                [(176, 82), (-176, 82), (-176, 86), (176, 86)],
                [(176, 82), (184, 82), (184, 86), (176, 86)],
            ),
        ),
        (
            "equator_crossing",
            "edge",
            battery(
                [(178, -1), (-178, -1), (-178, 1), (178, 1)],
                [(178, -1), (182, -1), (182, 1), (178, 1)],
            ),
        ),
        (
            "southern_hemisphere",
            "edge",
            battery(
                [(-179, -70), (179, -70), (179, -65), (-179, -65)],
                [(-179, -70), (-181, -70), (-181, -65), (-179, -65)],
            ),
        ),
    ]
