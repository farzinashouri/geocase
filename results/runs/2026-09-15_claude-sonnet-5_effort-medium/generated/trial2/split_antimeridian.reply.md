```python
"""Split a shapely Polygon that crosses the antimeridian into valid pieces."""

from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import transform


def _crosses_antimeridian(polygon: Polygon) -> bool:
    rings = [polygon.exterior] + list(polygon.interiors)
    for ring in rings:
        coords = list(ring.coords)
        for (x1, _), (x2, _) in zip(coords, coords[1:]):
            if abs(x2 - x1) > 180:
                return True
    return False


def _shift_to_positive(x, y, z=None):
    return (x + 360.0 if x < 0 else x, y)


def _shift_back(x, y, z=None):
    return (x - 360.0, y)


def _flatten_polygons(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [g for g in geom.geoms if not g.is_empty]
    if hasattr(geom, "geoms"):
        result = []
        for g in geom.geoms:
            result.extend(_flatten_polygons(g))
        return result
    return []


def split_antimeridian(polygon: Polygon):
    """Split a lon/lat polygon crossing the antimeridian into valid pieces.

    Returns a list of shapely Polygons covering the same region as the
    input, none of which crosses the antimeridian (they may touch it
    only along an edge). Polygons that do not cross the antimeridian are
    returned unchanged as a single-element list.
    """
    if not _crosses_antimeridian(polygon):
        return [polygon]

    unwrapped = transform(_shift_to_positive, polygon)

    eastern_box = box(0, -90, 180, 90)
    western_box = box(180, -90, 360, 90)

    eastern_part = unwrapped.intersection(eastern_box)
    western_part = unwrapped.intersection(western_box)

    pieces = _flatten_polygons(eastern_part)

    western_polys = _flatten_polygons(western_part)
    for poly in western_polys:
        pieces.append(transform(_shift_back, poly))

    return pieces
```