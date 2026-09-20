```python
"""Project a WGS84 LineString into a projected CRS while preserving geodesic shape."""

from shapely.geometry import LineString
from pyproj import Geod, Transformer

_GEOD = Geod(ellps="WGS84")
_MAX_SEGMENT_M = 25_000.0


def _densify_segment(lon1, lat1, lon2, lat2):
    """Return intermediate (lon, lat) points so that no gap exceeds 25 km along the geodesic."""
    _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if dist <= _MAX_SEGMENT_M:
        return []
    n_intermediate = int(dist // _MAX_SEGMENT_M)
    pts = _GEOD.npts(lon1, lat1, lon2, lat2, n_intermediate)
    return pts


def project_line(line, dst_epsg):
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    dense_coords = [coords[0][:2]]
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        for pt in _densify_segment(lon1, lat1, lon2, lat2):
            dense_coords.append(pt)
        dense_coords.append((lon2, lat2))

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
    projected = [transformer.transform(lon, lat) for lon, lat in dense_coords]

    return LineString(projected)
```