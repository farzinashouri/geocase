"""Gates on where the catalog's cases actually are.

The defect these exist to prevent: 60 of the bundled vector cases are
format-transcodings of six hand-authored canonicals, so they inherit their
position from those six files. When all six sat in Thuringia and Copenhagen,
54% of the whole catalog fell inside a single one-degree box -- an unexamined
default that made the coverage map useless and left cross-zone reprojection
entirely untested.
"""

from __future__ import annotations

from collections import Counter

import pytest

from geocase.catalog.registry import get_registry

#: The six hand-authored GeoJSON canonicals every transcoding family derives
#: from. Their positions are the ones that matter: move one, move ten cases.
CANONICALS = (
    "simple_valid_polygon",
    "simple_valid_point",
    "simple_valid_linestring",
    "simple_valid_multipoint",
    "simple_valid_multilinestring",
    "simple_valid_multipolygon",
)


def _centroid(extent) -> tuple[float, float]:
    if extent.west > extent.east:  # antimeridian-wrapping box
        span = (180.0 - extent.west) + (extent.east + 180.0)
        lon = extent.west + span / 2.0
        if lon > 180.0:
            lon -= 360.0
    else:
        lon = (extent.west + extent.east) / 2.0
    return lon, (extent.south + extent.north) / 2.0


def _placed() -> list:
    return [case for case in get_registry().list_cases() if case.extent is not None]


def test_canonical_sources_are_geographically_distinct() -> None:
    """Six canonicals in one valley is six cases' worth of coverage, not six."""
    points = {
        case_id: _centroid(get_registry().get(case_id).extent) for case_id in CANONICALS
    }

    for i, left in enumerate(CANONICALS):
        for right in CANONICALS[i + 1 :]:
            lon_a, lat_a = points[left]
            lon_b, lat_b = points[right]
            separation = max(abs(lon_a - lon_b), abs(lat_a - lat_b))
            assert separation > 20.0, (
                f"{left} and {right} are {separation:.1f} degrees apart; "
                "the canonicals must not cluster"
            )


def test_no_single_degree_box_holds_more_than_a_fifth_of_the_catalog() -> None:
    """The clump, measured directly rather than by eye on the map."""
    placed = _placed()
    boxes = Counter()
    for case in placed:
        lon, lat = _centroid(case.extent)
        boxes[(int(lon // 1), int(lat // 1))] += 1

    box, count = boxes.most_common(1)[0]
    assert count <= len(placed) // 5, (
        f"{count} of {len(placed)} placed cases sit in the single 1-degree box at {box}"
    )


def test_catalog_covers_multiple_utm_zones() -> None:
    """One zone cannot test cross-zone behaviour, however many cases use it."""
    codes = set()
    for case in get_registry().list_cases():
        crs = str(case.crs or "")
        if crs.startswith("EPSG:"):
            code = crs.split(":", 1)[1]
            if code.startswith(("326", "327")) and len(code) == 5:
                codes.add(code)

    assert len(codes) >= 4, f"only {len(codes)} UTM zones in the catalog: {codes}"
    assert any(code.startswith("327") for code in codes), (
        "no southern-hemisphere UTM case; the 10 000 000 m false northing is untested"
    )

    northern = sorted(int(c[3:]) for c in codes if c.startswith("326"))
    assert any(b - a == 1 for a, b in zip(northern, northern[1:], strict=False)), (
        f"no adjacent northern zone pair in {northern}; "
        "cross-zone agreement cannot be asserted"
    )


def test_a_case_straddles_a_utm_zone_boundary() -> None:
    """The case that makes cross-zone reprojection testable at all."""
    straddlers = [
        case
        for case in get_registry().list_cases()
        if "utm_zone_boundary" in case.tags and case.extent is not None
    ]
    assert straddlers, "no case tagged utm_zone_boundary"

    # Every tagged case must actually cross a zone edge -- that is what the tag
    # claims, and a tag that can be wrong is worse than no tag.
    for case in straddlers:
        west, east = case.extent.west, case.extent.east
        crossed = [m for m in range(-180, 181, 6) if west < m < east]
        assert crossed, (
            f"{case.id} is tagged utm_zone_boundary but its extent "
            f"({west}, {east}) crosses no 6-degree meridian"
        )

    # At least one must additionally be stored *in* a single UTM CRS while
    # extending past that zone's edge. That is the case cross-zone
    # reprojection error is actually testable against; the adjacent-zone pair
    # is stored in WGS84 on purpose, so that both its features stay directly
    # comparable inside one GeoJSON collection.
    projected = [
        case for case in straddlers if str(case.crs or "").startswith("EPSG:32")
    ]
    assert projected, (
        "no utm_zone_boundary case declares a single UTM CRS; without one, a "
        "consumer that re-zones per vertex cannot be caught"
    )


@pytest.mark.parametrize(
    "case_id", ["utm_zone_1n_small", "utm_zone_56s_small", "utm_zone_boundary_straddle"]
)
def test_new_utm_cases_are_registered(case_id: str) -> None:
    assert get_registry().get(case_id) is not None
