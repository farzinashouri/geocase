```python
"""Project a WGS84 LineString into a projected CRS while tracing geodesics.

The straight segments of an EPSG:4326 LineString are interpreted as
geodesics (shortest paths on the WGS84 ellipsoid). Each segment is
densified along its geodesic so that, once projected, the polyline
stays within the required tolerance of the true geodesic course.
"""

from __future__ import annotations

import math

import numpy as np
from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Maximum geodesic spacing between emitted vertices, in metres. With
# vertices this close together the projected chord between them departs
# from the true geodesic by far less than the 25 km tolerance for any
# reasonable projected CRS.
_MAX_SPACING_M = 10_000.0


def _densify_segment(geod: Geod, lon1: float, lat1: float,
                     lon2: float, lat2: float) -> list[tuple[float, float]]:
    """Return points along the geodesic from (lon1, lat1) to (lon2, lat2).

    The start point is included, the end point is excluded, so consecutive
    segments can be concatenated without duplicating shared vertices.
    """
    _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist <= 0.0:
        return [(lon1, lat1)]
    n_intervals = max(1, int(math.ceil(dist / _MAX_SPACING_M)))
    if n_intervals == 1:
        return [(lon1, lat1)]
    inner = geod.npts(lon1, lat1, lon2, lat2, n_intervals - 1)
    return [(lon1, lat1)] + [(float(x), float(y)) for x, y in inner]


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 LineString to ``dst_epsg`` following geodesic courses.

    Parameters
    ----------
    line:
        A shapely LineString with (longitude, latitude) coordinates in
        EPSG:4326.
    dst_epsg:
        Integer EPSG code of the destination projected CRS.

    Returns
    -------
    LineString
        A LineString in the destination CRS whose vertices lie on the
        geodesic between each pair of consecutive input vertices, spaced
        closely enough that the projected polyline is within 25 km of the
        geodesic everywhere.
    """
    coords = np.asarray(line.coords, dtype=float)
    if coords.ndim != 2 or coords.shape[0] < 2:
        raise ValueError("line must contain at least two vertices")
    lons = coords[:, 0]
    lats = coords[:, 1]

    geod = Geod(ellps="WGS84")
    dense: list[tuple[float, float]] = []
    for i in range(len(lons) - 1):
        dense.extend(
            _densify_segment(geod, float(lons[i]), float(lats[i]),
                             float(lons[i + 1]), float(lats[i + 1]))
        )
    dense.append((float(lons[-1]), float(lats[-1])))

    transformer = Transformer.from_crs(
        "EPSG:4326", f"EPSG:{int(dst_epsg)}", always_xy=True
    )
    arr = np.asarray(dense, dtype=float)
    xs, ys = transformer.transform(arr[:, 0], arr[:, 1])
    return LineString(np.column_stack([xs, ys]))
```