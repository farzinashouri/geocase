```python
"""Project geodesic LineStrings from EPSG:4326 into a projected CRS."""

from shapely.geometry import LineString
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")
_MAX_SEGMENT_M = 25_000.0


def _densify_segment(lon1, lat1, lon2, lat2):
    """Return intermediate (lon, lat) points between two vertices such that
    consecutive points are within _MAX_SEGMENT_M of each other along the
    geodesic, excluding the start point but including the end point."""
    _, _, distance_m = _GEOD.inv(lon1, lat1, lon2, lat2)

    if distance_m <= _MAX_SEGMENT_M:
        return [(lon2, lat2)]

    npts = int(distance_m // _MAX_SEGMENT_M)
    intermediates = _GEOD.npts(lon1, lat1, lon2, lat2, npts)
    return intermediates + [(lon2, lat2)]


def project_line(line, dst_epsg):
    from pyproj import Transformer

    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    densified = [coords[0][:2]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        densified.extend(_densify_segment(lon1, lat1, lon2, lat2))

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
    projected = [transformer.transform(lon, lat) for lon, lat in densified]

    return LineString(projected)
```