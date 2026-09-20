"""Project a WGS84 (EPSG:4326) LineString into a projected CRS, densifying so
that the projected polyline follows the true geodesic course.

The output polyline stays within ``TOLERANCE_M`` (25 km) of the projected
image of the ellipsoidal geodesic that joins each pair of consecutive input
vertices.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Sequence, Tuple

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "TOLERANCE_M"]


#: Required maximum deviation, in metres of the destination CRS, between the
#: returned polyline and the projected geodesic.
TOLERANCE_M = 25_000.0

# Refine against a tighter budget than the contract: the midpoint test samples
# the error rather than bounding it, so we leave headroom.
_TARGET_M = 0.4 * TOLERANCE_M

# No initial segment longer than this (geodesic metres) is handed to the
# adaptive pass. It guarantees a dense enough starting sampling that the
# midpoint test cannot step over a bulge in a strongly distorted region.
_MAX_INITIAL_SEG_M = 100_000.0

# Stop subdividing once a geodesic sub-segment is this short: at that length a
# chord cannot deviate from the geodesic by anything near the tolerance.
_MIN_SEG_M = 50.0

_MAX_DEPTH = 24

_GEOD = Geod(ellps="WGS84")


@lru_cache(maxsize=32)
def _transformer(dst_epsg: int) -> Transformer:
    dst = CRS.from_epsg(dst_epsg)
    if not dst.is_projected:
        raise ValueError(f"EPSG:{dst_epsg} is not a projected CRS")
    return Transformer.from_crs(CRS.from_epsg(4326), dst, always_xy=True)


def _finite(xy: Tuple[float, float]) -> bool:
    return math.isfinite(xy[0]) and math.isfinite(xy[1])


def _point_segment_distance(
    p: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float],
) -> float:
    """Distance from ``p`` to the segment ``a``-``b`` in the projected plane."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx = bx - ax
    dy = by - ay
    den = dx * dx + dy * dy
    if den == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / den
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _geodesic_midpoint(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> Tuple[float, float, float]:
    """Return ``(lon, lat, geodesic_length)`` for the midpoint of a geodesic."""
    az12, _az21, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist == 0.0:
        return lon1, lat1, 0.0
    mlon, mlat, _ = _GEOD.fwd(lon1, lat1, az12, dist / 2.0)
    return mlon, mlat, dist


def _refine(
    lon1: float,
    lat1: float,
    xy1: Tuple[float, float],
    lon2: float,
    lat2: float,
    xy2: Tuple[float, float],
    seg_len: float,
    tf: Transformer,
    out: List[Tuple[float, float]],
    depth: int,
) -> None:
    """Append the projected interior points of the geodesic, then ``xy2``.

    ``out`` already ends with ``xy1``.
    """
    if seg_len <= _MIN_SEG_M or depth >= _MAX_DEPTH:
        out.append(xy2)
        return

    mlon, mlat, _ = _geodesic_midpoint(lon1, lat1, lon2, lat2)
    mxy = tf.transform(mlon, mlat)

    if _finite(xy1) and _finite(xy2) and _finite(mxy):
        if _point_segment_distance(mxy, xy1, xy2) <= _TARGET_M:
            out.append(xy2)
            return
    elif not _finite(mxy):
        # The midpoint falls outside the projection's domain; subdividing
        # further cannot produce a usable error estimate.
        out.append(xy2)
        return

    half = seg_len / 2.0
    _refine(lon1, lat1, xy1, mlon, mlat, mxy, half, tf, out, depth + 1)
    _refine(mlon, mlat, mxy, lon2, lat2, xy2, half, tf, out, depth + 1)


def _initial_split(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> List[Tuple[float, float]]:
    """Geodesic points strictly between the endpoints, spaced <= 100 km."""
    az12, _az21, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist <= _MAX_INITIAL_SEG_M:
        return []
    n = int(math.ceil(dist / _MAX_INITIAL_SEG_M)) - 1
    step = dist / (n + 1)
    return [_GEOD.fwd(lon1, lat1, az12, step * (i + 1))[:2] for i in range(n)]


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a lon/lat ``LineString`` into ``EPSG:<dst_epsg>``.

    Each pair of consecutive input vertices is joined by the ellipsoidal
    geodesic between them, densified so that the returned polyline is within
    25 km of that geodesic's projected image everywhere.

    Parameters
    ----------
    line:
        A shapely ``LineString`` with longitude/latitude coordinates in
        EPSG:4326.
    dst_epsg:
        EPSG code of the projected destination CRS.

    Returns
    -------
    LineString
        The densified line in the destination CRS.
    """
    if not isinstance(line, LineString):
        raise TypeError("line must be a shapely LineString")

    tf = _transformer(int(dst_epsg))

    if line.is_empty:
        return LineString()

    coords: Sequence[Tuple[float, ...]] = list(line.coords)
    lonlat = [(float(c[0]), float(c[1])) for c in coords]

    if len(lonlat) < 2:
        return LineString([tf.transform(*lonlat[0])] * 2) if lonlat else LineString()

    out: List[Tuple[float, float]] = [tf.transform(*lonlat[0])]

    for (lon1, lat1), (lon2, lat2) in zip(lonlat, lonlat[1:]):
        # Pre-split long segments so the adaptive midpoint test starts from a
        # sampling fine enough not to miss local excursions.
        waypoints = [(lon1, lat1)] + _initial_split(lon1, lat1, lon2, lat2)
        waypoints.append((lon2, lat2))

        for (alon, alat), (blon, blat) in zip(waypoints, waypoints[1:]):
            axy = out[-1]
            bxy = tf.transform(blon, blat)
            _, _, seg_len = _geodesic_midpoint(alon, alat, blon, blat)
            if seg_len == 0.0:
                out.append(bxy)
                continue
            _refine(alon, alat, axy, blon, blat, bxy, seg_len, tf, out, 0)

    # Drop exact consecutive duplicates introduced by repeated input vertices.
    deduped: List[Tuple[float, float]] = [out[0]]
    for xy in out[1:]:
        if xy != deduped[-1]:
            deduped.append(xy)
    if len(deduped) < 2:
        deduped.append(deduped[0])

    return LineString(deduped)