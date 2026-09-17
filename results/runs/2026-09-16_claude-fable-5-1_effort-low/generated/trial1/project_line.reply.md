```python
"""Project a WGS84 LineString into a projected CRS along geodesic courses.

The output polyline follows the geodesic between each pair of consecutive
input vertices to within 25 km everywhere along the line, by densifying each
segment on the ellipsoid before projecting.
"""

from __future__ import annotations

import math

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Spacing (metres) between densified vertices along each geodesic segment.
# A 25 km chord on the WGS84 ellipsoid deviates from the geodesic by well
# under 25 m, so the projected polyline is far inside the 25 km tolerance.
_MAX_SPACING_M = 25_000.0
_TOLERANCE_M = 25_000.0

_GEOD = Geod(ellps="WGS84")


def _densify_segment(lon1: float, lat1: float, lon2: float, lat2: float) -> list[tuple[float, float]]:
    """Return points (excluding the start, including the end) along the geodesic."""
    _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist <= _MAX_SPACING_M:
        return [(lon2, lat2)]
    n_intermediate = int(math.ceil(dist / _MAX_SPACING_M)) - 1
    pts = _GEOD.npts(lon1, lat1, lon2, lat2, n_intermediate)
    return [(float(x), float(y)) for x, y in pts] + [(lon2, lat2)]


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a lon/lat (EPSG:4326) LineString to ``dst_epsg`` along geodesics.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Input line with coordinates ordered (longitude, latitude) in EPSG:4326.
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.geometry.LineString
        Line in the target CRS whose vertices trace the geodesic course
        between consecutive input vertices to within 25 km.
    """
    if line.is_empty:
        return LineString()

    coords = [(float(c[0]), float(c[1])) for c in line.coords]
    if len(coords) < 2:
        raise ValueError("LineString must have at least two vertices")

    dense: list[tuple[float, float]] = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        if lon1 == lon2 and lat1 == lat2:
            dense.append((lon2, lat2))
            continue
        dense.extend(_densify_segment(lon1, lat1, lon2, lat2))

    transformer = Transformer.from_crs(4326, int(dst_epsg), always_xy=True)
    lons = [p[0] for p in dense]
    lats = [p[1] for p in dense]
    xs, ys = transformer.transform(lons, lats)

    projected = [
        (float(x), float(y))
        for x, y in zip(xs, ys)
        if math.isfinite(x) and math.isfinite(y)
    ]
    if len(projected) < 2:
        raise ValueError(
            f"Line could not be projected into EPSG:{dst_epsg}; "
            "all or nearly all vertices fall outside the CRS domain"
        )
    return LineString(projected)


__all__ = ["project_line"]
```