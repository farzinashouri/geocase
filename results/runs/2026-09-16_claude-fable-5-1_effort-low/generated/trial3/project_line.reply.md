```python
"""Project a WGS84 LineString into a projected CRS while following geodesics.

The straight segments of an EPSG:4326 LineString are interpreted as geodesic
(shortest-path-on-the-ellipsoid) courses.  Each segment is densified along the
geodesic before being projected so that the resulting projected polyline stays
within a tight tolerance of the true geodesic course.
"""

from __future__ import annotations

import math

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Maximum geodesic length of a single densified segment, in metres.  The
# required tolerance is 25 km; a 5 km step keeps the chord sagitta on the
# ellipsoid at roughly 0.5 m, leaving an enormous margin for projection
# distortion (even at high latitudes in Mercator-style projections).
_STEP_M = 5_000.0

_GEOD = Geod(ellps="WGS84")


def _densify_segment(lon1, lat1, lon2, lat2):
    """Return (lon, lat) points along the geodesic from p1 to p2.

    Includes the start point, excludes the end point.
    """
    _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist <= 0.0:
        return [(lon1, lat1)]
    n_segments = max(1, int(math.ceil(dist / _STEP_M)))
    pts = [(lon1, lat1)]
    if n_segments > 1:
        pts.extend(_GEOD.npts(lon1, lat1, lon2, lat2, n_segments - 1))
    return pts


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 LineString into ``EPSG:dst_epsg`` following geodesics.

    Parameters
    ----------
    line:
        A shapely ``LineString`` with (longitude, latitude) coordinates in
        EPSG:4326.
    dst_epsg:
        Integer EPSG code of a projected coordinate reference system.

    Returns
    -------
    LineString
        A ``LineString`` in the target CRS whose vertices trace the geodesic
        between each pair of consecutive input vertices to well within 25 km.
    """
    coords = [(float(c[0]), float(c[1])) for c in line.coords]
    if len(coords) < 2:
        raise ValueError("project_line requires a LineString with at least two vertices")

    lonlat = []
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        lonlat.extend(_densify_segment(lon1, lat1, lon2, lat2))
    lonlat.append(coords[-1])

    transformer = Transformer.from_crs(
        "EPSG:4326", f"EPSG:{int(dst_epsg)}", always_xy=True
    )
    lons = [p[0] for p in lonlat]
    lats = [p[1] for p in lonlat]
    xs, ys = transformer.transform(lons, lats)

    projected = []
    for x, y in zip(xs, ys):
        if math.isfinite(x) and math.isfinite(y):
            projected.append((x, y))
    if len(projected) < 2:
        raise ValueError(
            f"Line could not be projected into EPSG:{dst_epsg} (outside CRS domain)"
        )
    return LineString(projected)
```