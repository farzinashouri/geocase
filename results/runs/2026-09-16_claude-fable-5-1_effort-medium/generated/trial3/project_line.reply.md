Here is the module.

```python
"""Project an EPSG:4326 LineString into a projected CRS along geodesic paths.

The output traces the WGS84 geodesic between each pair of consecutive input
vertices, densified so that the straight projected segments never depart from
the true geodesic course by more than 25 km.
"""

from __future__ import annotations

import math

import numpy as np
from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Tolerance required by the contract, in metres.
_TOLERANCE_M = 25_000.0

# Maximum spacing between consecutive output vertices along the geodesic, in
# metres.  The sagitta of a chord of length L on a sphere of radius R is about
# L^2 / (8 R); at 50 km that is roughly 50 m on the WGS84 ellipsoid, leaving a
# safety factor of several hundred against the 25 km tolerance even for
# projections with large scale distortion (e.g. Mercator at high latitudes)
# or where the straight projected segment is not a chord (rhumb lines).
_MAX_SPACING_M = 50_000.0


def _densify_segment(geod: Geod, lon1: float, lat1: float, lon2: float, lat2: float):
    """Return (lons, lats) along the geodesic from p1 to p2, inclusive of p2
    but exclusive of p1 (so segments can be concatenated)."""
    _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist <= 0.0:
        return [lon2], [lat2]
    n_pieces = max(1, int(math.ceil(dist / _MAX_SPACING_M)))
    n_inner = n_pieces - 1
    lons, lats = [], []
    if n_inner > 0:
        for lon, lat in geod.npts(lon1, lat1, lon2, lat2, n_inner):
            lons.append(lon)
            lats.append(lat)
    lons.append(lon2)
    lats.append(lat2)
    return lons, lats


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a lon/lat (EPSG:4326) LineString into the projected CRS with
    EPSG code ``dst_epsg``, following geodesics between input vertices.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Input line with coordinates as (longitude, latitude) in degrees.
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.geometry.LineString
        Line in the target CRS whose vertices lie on the WGS84 geodesic
        between consecutive input vertices, spaced closely enough that the
        line is within 25 km of the geodesic course everywhere.
    """
    if not isinstance(line, LineString):
        raise TypeError("line must be a shapely LineString")
    if line.is_empty:
        return LineString()

    coords = np.asarray(line.coords, dtype=float)[:, :2]
    if len(coords) < 2:
        raise ValueError("LineString must have at least two vertices")

    geod = Geod(ellps="WGS84")

    lons = [float(coords[0, 0])]
    lats = [float(coords[0, 1])]
    for i in range(len(coords) - 1):
        lon1, lat1 = float(coords[i, 0]), float(coords[i, 1])
        lon2, lat2 = float(coords[i + 1, 0]), float(coords[i + 1, 1])
        seg_lons, seg_lats = _densify_segment(geod, lon1, lat1, lon2, lat2)
        lons.extend(seg_lons)
        lats.extend(seg_lats)

    transformer = Transformer.from_crs(
        "EPSG:4326", f"EPSG:{int(dst_epsg)}", always_xy=True
    )
    xs, ys = transformer.transform(np.asarray(lons), np.asarray(lats))
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    finite = np.isfinite(xs) & np.isfinite(ys)
    if not finite.all():
        raise ValueError(
            "Some vertices could not be projected into EPSG:%d" % int(dst_epsg)
        )

    return LineString(np.column_stack([xs, ys]))
```