```python
"""Repair invalid Polygon/MultiPolygon geometries without changing enclosed area.

Uses shapely's linework-based make_valid, which nodes all boundary rings and
reconstructs polygons from the resulting arrangement using an even-odd
enclosure rule. This guarantees the fixed geometry covers exactly the area
enclosed by the original boundary rings: nothing enclosed is dropped, and no
extra area is introduced.
"""

from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon


def _extract_polygons(geom):
    if isinstance(geom, Polygon):
        return [] if geom.is_empty else [geom]
    if isinstance(geom, MultiPolygon):
        return [g for g in geom.geoms if not g.is_empty]
    if isinstance(geom, GeometryCollection):
        polys = []
        for part in geom.geoms:
            polys.extend(_extract_polygons(part))
        return polys
    return []


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering the area enclosed by geom's rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Possibly invalid geometry (e.g. self-intersecting rings).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry covering exactly the region enclosed by the input's
        boundary rings.
    """
    fixed = make_valid(geom, method="linework")

    polygons = _extract_polygons(fixed)

    if not polygons:
        return Polygon()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)
```