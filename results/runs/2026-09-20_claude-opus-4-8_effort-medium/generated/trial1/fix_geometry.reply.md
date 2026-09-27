```python
"""Repair invalid shapely polygonal geometries.

Provides :func:`fix_geometry`, which turns a possibly-invalid ``Polygon`` or
``MultiPolygon`` into a valid geometry covering exactly the region enclosed by
the input's boundary rings.
"""

from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid


def _polygonal_parts(geom):
    """Yield the ``Polygon`` components contained in *geom*, if any."""
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon):
        for part in geom.geoms:
            if not part.is_empty:
                yield part
    elif isinstance(geom, GeometryCollection):
        for part in geom.geoms:
            yield from _polygonal_parts(part)
    # Points and lines carry no area and are discarded.


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` for *geom*.

    The result covers exactly the area enclosed by the input's boundary rings:
    no enclosed location is dropped and no new area is introduced. An already
    valid input is returned covering the same region.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("fix_geometry expects a shapely geometry")
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("fix_geometry expects a Polygon or MultiPolygon")

    if geom.is_empty:
        return geom if isinstance(geom, MultiPolygon) else MultiPolygon()

    if geom.is_valid:
        result = geom
    else:
        # make_valid resolves self-intersections using the OGC interpretation,
        # preserving the area on each side of the boundary. It may return a
        # GeometryCollection mixing polygons with degenerate lines/points.
        repaired = make_valid(geom)
        parts = list(_polygonal_parts(repaired))
        if not parts:
            return MultiPolygon()
        # Merge touching parts back into a clean, non-overlapping geometry.
        result = unary_union(parts)

    if isinstance(result, Polygon):
        return result
    if isinstance(result, MultiPolygon):
        return result

    parts = list(_polygonal_parts(result))
    if not parts:
        return MultiPolygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)
```