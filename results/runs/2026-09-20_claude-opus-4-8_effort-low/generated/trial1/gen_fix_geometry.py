"""Repair invalid shapely polygonal geometries.

Provides :func:`fix_geometry`, which turns a possibly-invalid ``Polygon`` or
``MultiPolygon`` into a valid one covering exactly the region enclosed by the
input's boundary rings.
"""

from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid


def _collect_polygons(geom):
    """Yield every Polygon contained in ``geom``, discarding lower-dimensional
    pieces (points/lines) that ``make_valid`` may emit along self-intersections.
    """
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)):
        for part in geom.geoms:
            yield from _collect_polygons(part)
    # Points and lines carry no area and are dropped.


def fix_geometry(geom):
    """Return a valid ``Polygon`` or ``MultiPolygon`` covering exactly the area
    enclosed by ``geom``'s boundary rings.

    ``make_valid`` reconstructs a topologically valid geometry from the input's
    rings without adding or removing enclosed area, so a self-intersecting
    "bow-tie" becomes a MultiPolygon of its two lobes and an already-valid
    input is returned unchanged in coverage.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("geom must be a Polygon or MultiPolygon")

    if geom.is_valid:
        repaired = geom
    else:
        repaired = make_valid(geom)

    polygons = list(_collect_polygons(repaired))

    if not polygons:
        return Polygon()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)