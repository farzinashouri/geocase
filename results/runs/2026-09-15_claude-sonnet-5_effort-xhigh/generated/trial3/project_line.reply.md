```python
"""Project a WGS84 LineString into a projected CRS while preserving the
true geodesic shape of each input segment to within a fixed tolerance.
"""

from __future__ import annotations

from shapely.geometry import LineString
from pyproj import Geod, Transformer

_GEOD = Geod(ellps="WGS84")

# Required accuracy is 25 km; stay comfortably under that so recursive
# midpoint sampling (which approximates, rather than proves, the true
# maximum deviation of a segment) still lands inside the bound.
_TOLERANCE_M = 20_000.0
_MAX_DEPTH = 24


def _geodesic_midpoint(lon1, lat1, lon2, lat2):
    return _GEOD.npts(lon1, lat1, lon2, lat2, 1)[0]


def _deviation_m(transformer, transformer_inv, lon1, lat1, lon2, lat2, mid_lon, mid_lat):
    x1, y1 = transformer.transform(lon1, lat1)
    x2, y2 = transformer.transform(lon2, lat2)
    chord_x, chord_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    chord_lon, chord_lat = transformer_inv.transform(chord_x, chord_y)
    _, _, dist = _GEOD.inv(mid_lon, mid_lat, chord_lon, chord_lat)
    return dist


def _densify_segment(transformer, transformer_inv, lon1, lat1, lon2, lat2, depth=0):
    """Return the list of intermediate + end lon/lat points needed so the
    straight chord between (lon1, lat1) and (lon2, lat2), once projected,
    stays within tolerance of the true geodesic between them.
    """
    if (lon1, lat1) == (lon2, lat2):
        return []

    mid_lon, mid_lat = _geodesic_midpoint(lon1, lat1, lon2, lat2)

    if depth >= _MAX_DEPTH:
        return [(lon2, lat2)]

    dist = _deviation_m(transformer, transformer_inv, lon1, lat1, lon2, lat2, mid_lon, mid_lat)
    if dist <= _TOLERANCE_M:
        return [(lon2, lat2)]

    left = _densify_segment(transformer, transformer_inv, lon1, lat1, mid_lon, mid_lat, depth + 1)
    right = _densify_segment(transformer, transformer_inv, mid_lon, mid_lat, lon2, lat2, depth + 1)
    return left + right


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Reproject a lon/lat (EPSG:4326) LineString into ``dst_epsg``.

    Consecutive input vertices are treated as endpoints of geodesics on
    the WGS84 ellipsoid. The returned line is densified with as many
    extra vertices as needed so it traces each geodesic to within 25 km
    everywhere along its length.
    """
    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    transformer_inv = Transformer.from_crs(dst_epsg, 4326, always_xy=True)

    coords = [(c[0], c[1]) for c in line.coords]

    dense_lonlat = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        dense_lonlat.extend(
            _densify_segment(transformer, transformer_inv, lon1, lat1, lon2, lat2)
        )

    projected = [transformer.transform(lon, lat) for lon, lat in dense_lonlat]
    return LineString(projected)
```