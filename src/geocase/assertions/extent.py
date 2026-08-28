"""Extent assertions — is the data where its metadata says it is?

The catalog publishes a WGS84 ``extent`` per case, and the whole value of a
generated field is that it cannot drift from the data. This is the check that
enforces that, and it is the same code the content gate runs (see
:mod:`geocase.catalog.content`) -- a gate that passed while a user's identical
assertion failed would be worse than no gate.

The one subtlety is the antimeridian. A case may store unwrapped longitudes
(``dateline_crossing_polygon`` really does have coordinates at 190), while the
declared extent stores the wrapped form (``west=170, east=-170``). Those are
the *same box*; comparing them numerically without folding first reports a
340-degree error on a case that is perfectly correct.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geocase.catalog.models import SpatialExtent


#: Degrees of slack allowed between an observed bound and a declared one.
#: Extents are written rounded to six decimals, and a reprojection round-trip
#: moves the last digits, so the tolerance has to clear both without being
#: loose enough to hide a case that genuinely moved. 1e-4 degrees is ~11 m.
DEFAULT_TOLERANCE = 1e-4


def _wrap_longitude(lon: float) -> float:
    """Fold a longitude into [-180, 180], keeping 180 as the eastern form."""
    wrapped = (float(lon) + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 and lon > 0 else wrapped


def _normalize(
    west: float, south: float, east: float, north: float
) -> tuple[float, float, float, float]:
    """Reduce a raw lon/lat envelope to the catalog's wrap convention."""
    if east - west > 180.0:
        west, east = _wrap_longitude(east), _wrap_longitude(west)
    else:
        west, east = _wrap_longitude(west), _wrap_longitude(east)
    return west, float(south), east, float(north)


def assert_bounds(
    observed: tuple[float, float, float, float],
    expected: SpatialExtent,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    msg: str | None = None,
) -> None:
    """Assert a ``(west, south, east, north)`` envelope matches *expected*.

    *observed* is a raw WGS84 envelope as a reader hands it over --
    ``gdf.total_bounds`` or ``transform_bounds(...)`` -- and may carry
    unwrapped longitudes past 180. It is folded to the catalog's convention
    before comparison, so an antimeridian case compares as the box it is.

    Raises :class:`AssertionError` naming the axis that moved and by how far,
    because "the extent is wrong" without a direction is not actionable.
    """
    west, south, east, north = _normalize(*observed)
    pairs = (
        ("west", west, expected.west),
        ("south", south, expected.south),
        ("east", east, expected.east),
        ("north", north, expected.north),
    )

    drifted = [
        f"{name} {actual:.6f} != {declared:.6f} "
        f"(off by {abs(actual - declared):.6f} degrees)"
        for name, actual, declared in pairs
        if abs(actual - declared) > tolerance
    ]
    if drifted:
        raise AssertionError(
            msg
            or "Declared extent does not match the data: "
            + "; ".join(drifted)
            + ". Regenerate with scripts/catalog_extent.py --write"
        )
