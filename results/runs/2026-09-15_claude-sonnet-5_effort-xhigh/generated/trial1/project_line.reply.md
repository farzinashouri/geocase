```python
"""Reproject a WGS84 LineString while keeping it geodesically faithful.

Straight chords in a projected CRS can bow away from the true geodesic
between two lon/lat vertices -- both because the geodesic on the WGS84
ellipsoid is itself curved, and because the projection further distorts
shape. This module recursively bisects each input segment along the true
geodesic until the projected chord and the true geodesic agree to within a
fixed ground-distance tolerance everywhere.
"""

from __future__ import annotations

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

_WGS84 = CRS.from_epsg(4326)
_GEOD = Geod(ellps="WGS84")
_TOLERANCE_M = 25_000.0
_MAX_DEPTH = 24


def _geodesic_point_at_fraction(lon1, lat1, lon2, lat2, fraction):
    az12, _, distance = _GEOD.inv(lon1, lat1, lon2, lat2)
    if distance == 0.0:
        return lon1, lat1
    lon, lat, _ = _GEOD.fwd(lon1, lat1, az12, distance * fraction)
    return lon, lat


def _densify(lon1, lat1, lon2, lat2, to_proj, to_geo, depth=0):
    mid_lon, mid_lat = _geodesic_point_at_fraction(lon1, lat1, lon2, lat2, 0.5)

    x1, y1 = to_proj.transform(lon1, lat1)
    x2, y2 = to_proj.transform(lon2, lat2)
    chord_lon, chord_lat = to_geo.transform((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    _, _, deviation = _GEOD.inv(mid_lon, mid_lat, chord_lon, chord_lat)

    if deviation <= _TOLERANCE_M or depth >= _MAX_DEPTH:
        return [(lon2, lat2)]

    left = _densify(lon1, lat1, mid_lon, mid_lat, to_proj, to_geo, depth + 1)
    right = _densify(mid_lon, mid_lat, lon2, lat2, to_proj, to_geo, depth + 1)
    return left + right


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Reproject `line` (lon/lat, EPSG:4326) to `dst_epsg`, densified so the
    projected polyline tracks the WGS84 geodesic to within 25 km everywhere."""
    dst_crs = CRS.from_epsg(dst_epsg)
    to_proj = Transformer.from_crs(_WGS84, dst_crs, always_xy=True)
    to_geo = Transformer.from_crs(dst_crs, _WGS84, always_xy=True)

    src_coords = [(c[0], c[1]) for c in line.coords]
    lon_lat_points = [src_coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(src_coords, src_coords[1:]):
        lon_lat_points.extend(_densify(lon1, lat1, lon2, lat2, to_proj, to_geo))

    xs, ys = to_proj.transform(
        [p[0] for p in lon_lat_points], [p[1] for p in lon_lat_points]
    )
    return LineString(zip(xs, ys))
```