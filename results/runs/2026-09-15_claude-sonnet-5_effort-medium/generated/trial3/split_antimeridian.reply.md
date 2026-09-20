```python
"""Split polygons that cross the antimeridian into valid, non-crossing pieces."""

import math

from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry


def _crosses_antimeridian(polygon):
    rings = [polygon.exterior] + list(polygon.interiors)
    for ring in rings:
        coords = list(ring.coords)
        for (lon1, _), (lon2, _) in zip(coords, coords[1:]):
            if abs(lon2 - lon1) > 180:
                return True
    return False


def _unwrap_ring(coords):
    result = [coords[0]]
    offset = 0.0
    lon_prev = coords[0][0]
    for lon, lat in coords[1:]:
        diff = lon - lon_prev
        if diff > 180:
            offset -= 360
        elif diff < -180:
            offset += 360
        lon_prev = lon
        result.append((lon + offset, lat))
    return result


def _align_ring(ring, ext_minx, ext_maxx):
    ext_mid = (ext_minx + ext_maxx) / 2.0
    ring_mid = sum(lon for lon, _ in ring) / len(ring)
    k = round((ext_mid - ring_mid) / 360.0)
    if k == 0:
        return ring
    return [(lon + k * 360, lat) for lon, lat in ring]


def _unwrap_polygon(polygon):
    ext = _unwrap_ring(list(polygon.exterior.coords))
    ext_lons = [lon for lon, _ in ext]
    ext_minx, ext_maxx = min(ext_lons), max(ext_lons)

    interiors = []
    for interior in polygon.interiors:
        ring = _unwrap_ring(list(interior.coords))
        ring = _align_ring(ring, ext_minx, ext_maxx)
        interiors.append(ring)

    return Polygon(ext, interiors)


def _flatten_polygons(geom, out):
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        if geom.area > 1e-12:
            out.append(geom)
    elif geom.geom_type == "GeometryCollection":
        for part in geom.geoms:
            _flatten_polygons(part, out)
    elif geom.geom_type == "MultiPolygon":
        for part in geom.geoms:
            if part.area > 1e-12:
                out.append(part)


def split_antimeridian(polygon):
    """Split a lon/lat Polygon that may cross the antimeridian.

    Returns a list of Polygons covering the same region as ``polygon``,
    none of which crosses the antimeridian (except touching it at an edge).
    """
    if not _crosses_antimeridian(polygon):
        return [polygon]

    unwrapped = _unwrap_polygon(polygon)
    minx, miny, maxx, maxy = unwrapped.bounds

    k_start = math.floor((minx + 180) / 360)
    k_end = math.floor((maxx + 180 - 1e-9) / 360)

    pieces = []
    for k in range(k_start, k_end + 1):
        strip = box(k * 360 - 180, -90, k * 360 + 180, 90)
        clipped = unwrapped.intersection(strip)
        parts = []
        _flatten_polygons(clipped, parts)
        for part in parts:
            shifted_coords_ext = [(lon - k * 360, lat) for lon, lat in part.exterior.coords]
            shifted_interiors = [
                [(lon - k * 360, lat) for lon, lat in interior.coords]
                for interior in part.interiors
            ]
            shifted = Polygon(shifted_coords_ext, shifted_interiors)
            if not shifted.is_valid:
                shifted = shifted.buffer(0)
            result_parts = []
            if isinstance(shifted, BaseGeometry):
                _flatten_polygons(shifted, result_parts)
            pieces.extend(result_parts if result_parts else [shifted])

    return pieces
```