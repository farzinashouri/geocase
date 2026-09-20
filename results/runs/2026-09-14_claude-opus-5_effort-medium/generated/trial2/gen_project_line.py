"""Geodesic-faithful projection of WGS84 lines into a projected CRS.

`project_line` converts a shapely ``LineString`` whose coordinates are
longitude/latitude on EPSG:4326 into a ``LineString`` in a target projected
CRS.  Instead of simply projecting the input vertices (which would connect
them with straight lines in the target plane, and therefore with something
that is generally *not* the shortest path on the ellipsoid), every input
segment is densified along its geodesic until the straight chords of the
output polyline stay within 25 km of the true geodesic course everywhere.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Tuple

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line"]


#: Accuracy the output is required to meet, in metres.
MAX_DEVIATION_M = 25_000.0

#: Accuracy actually targeted while densifying.  The error estimator samples
#: the deviation at segment midpoints, which is close to but not exactly the
#: worst-case deviation, so we leave a healthy safety margin.
_TOLERANCE_M = MAX_DEVIATION_M / 2.5

#: No output chord ever spans more than this much geodesic distance.  This
#: guarantees the curvature of every input segment is sampled before the
#: adaptive test is trusted, so symmetric segments (whose midpoint happens to
#: fall on the chord) cannot terminate refinement prematurely.
_MAX_STEP_M = 100_000.0

#: Bisection depth limit below the initial uniform split.  Reached only near
#: projection singularities, where no finite densification converges.
_MAX_DEPTH = 16

_GEOD = Geod(ellps="WGS84")


@lru_cache(maxsize=32)
def _transformers(dst_epsg: int) -> Tuple[Transformer, Transformer, bool]:
    """Return (forward, inverse, target_is_projected) for EPSG:4326 -> dst."""
    dst = CRS.from_epsg(int(dst_epsg))
    src = CRS.from_epsg(4326)
    fwd = Transformer.from_crs(src, dst, always_xy=True)
    inv = Transformer.from_crs(dst, src, always_xy=True)
    return fwd, inv, dst.is_projected


def _geodesic_midpoint(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> Tuple[float, float, float]:
    """Midpoint of the geodesic from 1 to 2, plus the geodesic length."""
    az12, _az21, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist == 0.0:
        return lon1, lat1, 0.0
    mlon, mlat, _ = _GEOD.fwd(lon1, lat1, az12, dist / 2.0)
    return mlon, mlat, dist


def _finite(*values: float) -> bool:
    return all(math.isfinite(v) for v in values)


class _Densifier:
    """Adaptive geodesic densification for one target CRS."""

    def __init__(self, dst_epsg: int) -> None:
        self._fwd, self._inv, self._projected = _transformers(dst_epsg)

    def project(self, lon: float, lat: float) -> Tuple[float, float]:
        x, y = self._fwd.transform(lon, lat)
        if not _finite(x, y):
            raise ValueError(
                f"point ({lon}, {lat}) cannot be represented in the target CRS"
            )
        return float(x), float(y)

    def _deviation(
        self,
        mid_ll: Tuple[float, float],
        mid_xy: Tuple[float, float],
        chord_mid_xy: Tuple[float, float],
    ) -> float:
        """Estimated deviation, in metres, of the chord from the geodesic.

        Two complementary measures are combined: the planar offset in the
        target CRS and the corresponding ground distance on the ellipsoid.
        Whichever is larger drives refinement, so the result is faithful both
        as drawn in the projected plane and as measured on the ground.
        """
        error = 0.0

        if self._projected:
            error = math.hypot(
                mid_xy[0] - chord_mid_xy[0], mid_xy[1] - chord_mid_xy[1]
            )

        # Ground distance between the true geodesic midpoint and the point the
        # output line actually passes through at that place.
        clon, clat = self._inv.transform(chord_mid_xy[0], chord_mid_xy[1])
        if not _finite(clon, clat):
            return float("inf")
        _az, _baz, ground = _GEOD.inv(mid_ll[0], mid_ll[1], clon, clat)
        if not math.isfinite(ground):
            return float("inf")

        return max(error, ground)

    def _refine(
        self,
        p1: Tuple[float, float],
        xy1: Tuple[float, float],
        p2: Tuple[float, float],
        xy2: Tuple[float, float],
        depth: int,
    ) -> List[Tuple[float, float]]:
        """Interior projected vertices needed between p1 and p2, in order."""
        mlon, mlat, dist = _geodesic_midpoint(p1[0], p1[1], p2[0], p2[1])
        if dist == 0.0:
            return []

        mid_xy = self.project(mlon, mlat)
        chord_mid_xy = ((xy1[0] + xy2[0]) / 2.0, (xy1[1] + xy2[1]) / 2.0)

        if depth >= _MAX_DEPTH:
            return [mid_xy]

        if self._deviation((mlon, mlat), mid_xy, chord_mid_xy) <= _TOLERANCE_M:
            return []

        mid_ll = (mlon, mlat)
        left = self._refine(p1, xy1, mid_ll, mid_xy, depth + 1)
        right = self._refine(mid_ll, mid_xy, p2, xy2, depth + 1)
        return left + [mid_xy] + right

    def segment(
        self, p1: Tuple[float, float], p2: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Projected vertices for one input segment, excluding its start."""
        az12, _az21, dist = _GEOD.inv(p1[0], p1[1], p2[0], p2[1])
        if not math.isfinite(dist):
            raise ValueError(f"no geodesic between {p1} and {p2}")

        end_xy = self.project(*p2)
        if dist == 0.0:
            return [end_xy]

        # Uniform pre-split so curvature is always sampled, then adaptive
        # bisection of each piece.
        n = max(1, int(math.ceil(dist / _MAX_STEP_M)))
        nodes_ll = [p1]
        for i in range(1, n):
            lon, lat, _ = _GEOD.fwd(p1[0], p1[1], az12, dist * i / n)
            nodes_ll.append((lon, lat))
        nodes_ll.append(p2)

        nodes_xy = [self.project(*p1)]
        for node in nodes_ll[1:-1]:
            nodes_xy.append(self.project(*node))
        nodes_xy.append(end_xy)

        out: List[Tuple[float, float]] = []
        for i in range(n):
            out.extend(
                self._refine(
                    nodes_ll[i], nodes_xy[i], nodes_ll[i + 1], nodes_xy[i + 1], 0
                )
            )
            out.append(nodes_xy[i + 1])
        return out


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 ``LineString`` into ``dst_epsg``, tracing geodesics.

    Parameters
    ----------
    line:
        ``shapely.geometry.LineString`` with longitude/latitude coordinates in
        EPSG:4326 (x = longitude, y = latitude).
    dst_epsg:
        EPSG code of the target projected CRS.

    Returns
    -------
    LineString
        The line in the target CRS, densified so that it follows the geodesic
        between each pair of consecutive input vertices to within 25 km
        everywhere.  Any z/m values on the input are dropped.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a shapely LineString, got {type(line)!r}")

    if line.is_empty:
        return LineString()

    coords = [(float(c[0]), float(c[1])) for c in line.coords]

    # Collapse repeated vertices; they carry no geodesic information.
    cleaned: List[Tuple[float, float]] = [coords[0]]
    for pt in coords[1:]:
        if pt != cleaned[-1]:
            cleaned.append(pt)

    densifier = _Densifier(int(dst_epsg))

    if len(cleaned) == 1:
        # Degenerate input (all vertices identical): keep it degenerate.
        xy = densifier.project(*cleaned[0])
        return LineString([xy, xy])

    out: List[Tuple[float, float]] = [densifier.project(*cleaned[0])]
    for p1, p2 in zip(cleaned, cleaned[1:]):
        out.extend(densifier.segment(p1, p2))

    return LineString(out)