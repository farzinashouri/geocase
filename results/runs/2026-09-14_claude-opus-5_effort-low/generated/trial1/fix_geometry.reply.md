```python
"""Repair invalid polygonal geometries.

``fix_geometry`` takes a shapely ``Polygon`` or ``MultiPolygon`` that may be
invalid (self-intersecting rings, rings touching at a point, duplicated
vertices, ...) and returns a valid ``Polygon`` or ``MultiPolygon`` covering the
same region as the input's boundary linework: no enclosed area is lost and no
new area is introduced.

Importing this module has no side effects.
"""

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

__all__ = ["fix_geometry"]

_POLYGONAL = (Polygon, MultiPolygon)


def _polygonal_parts(geom):
    """Yield the polygonal components of *geom*, discarding lines and points.

    ``make_valid`` may return a ``GeometryCollection`` mixing polygons with the
    degenerate linework of collapsed slivers; only the areal parts describe the
    region we care about.
    """
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, (MultiPolygon, GeometryCollection)):
        for part in geom.geoms:
            yield from _polygonal_parts(part)


def fix_geometry(geom):
    """Return a valid ``Polygon``/``MultiPolygon`` covering the same region as *geom*.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Possibly invalid input geometry.

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry covering exactly the area enclosed by the input's
        boundary. An already-valid input comes back covering the same region.
        An empty input yields an empty ``Polygon``.

    Raises
    ------
    TypeError
        If *geom* is not a ``Polygon`` or ``MultiPolygon``.
    """
    if not isinstance(geom, _POLYGONAL):
        raise TypeError(
            "fix_geometry expects a Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )

    if geom.is_empty:
        return Polygon()

    # make_valid keeps the original linework and re-polygonizes it, so it never
    # invents area and never drops enclosed area. A valid geometry passes
    # through unchanged.
    repaired = geom if geom.is_valid else make_valid(geom)

    parts = list(_polygonal_parts(repaired))
    if not parts:
        return Polygon()

    # Dissolve so adjacent faces produced by the repair merge back together and
    # the result is a single clean Polygon/MultiPolygon.
    merged = unary_union(parts) if len(parts) > 1 else parts[0]

    if isinstance(merged, _POLYGONAL):
        if not merged.is_valid:
            # Defensive: re-run the repair on the dissolved result.
            merged = unary_union(list(_polygonal_parts(make_valid(merged))) or [Polygon()])
        return merged

    # unary_union collapsed to something non-areal (zero-area input).
    remaining = list(_polygonal_parts(merged))
    if not remaining:
        return Polygon()
    return remaining[0] if len(remaining) == 1 else MultiPolygon(remaining)
```