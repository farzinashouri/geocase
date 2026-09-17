```python
"""Repair invalid polygonal geometries without changing the enclosed region.

`fix_geometry` returns a valid Polygon or MultiPolygon covering exactly the
region enclosed by the input's boundary rings:

* every exterior ring contributes the union of all faces bounded by its
  (self-noded) linework, so a bowtie yields both lobes and a self-overlapping
  loop keeps its overlap and any inner loops covered;
* every interior ring contributes its enclosed region in the same way, and that
  region is subtracted from its own shell;
* the per-polygon results of a MultiPolygon are unioned.

A valid input is reproduced exactly (no nodes are inserted, so the faces are
the original rings).
"""

from __future__ import annotations

from typing import List, Sequence

import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]


def _ring_region(coords: Sequence) -> BaseGeometry:
    """Union of all faces enclosed by a single (possibly self-intersecting) ring."""
    coords = list(coords)
    if len(coords) < 4:
        return Polygon()
    line = LineString(coords)
    if line.is_empty or line.length == 0:
        return Polygon()
    noded = shapely.node(line)
    faces = list(polygonize(noded))
    if not faces:
        return Polygon()
    if len(faces) == 1:
        return faces[0]
    return unary_union(faces)


def _polygon_region(poly: Polygon) -> BaseGeometry:
    """Region of one Polygon: enclosed shell minus enclosed holes."""
    if poly.is_empty:
        return Polygon()
    shell = _ring_region(poly.exterior.coords)
    if shell.is_empty:
        return Polygon()
    holes = [
        h for h in (_ring_region(r.coords) for r in poly.interiors) if not h.is_empty
    ]
    if not holes:
        return shell
    hole_region = holes[0] if len(holes) == 1 else unary_union(holes)
    return shell.difference(hole_region)


def _polygonal_parts(geom: BaseGeometry) -> List[Polygon]:
    """Flatten any geometry into its non-degenerate Polygon components."""
    if geom is None or geom.is_empty:
        return []
    kind = geom.geom_type
    if kind == "Polygon":
        return [geom] if geom.area > 0 else []
    if kind in ("MultiPolygon", "GeometryCollection"):
        out: List[Polygon] = []
        for g in geom.geoms:
            out.extend(_polygonal_parts(g))
        return out
    return []


def _assemble(polys: List[Polygon]) -> BaseGeometry:
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)


def fix_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Return a valid Polygon/MultiPolygon covering exactly the region enclosed
    by ``geom``'s boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Possibly invalid input (self-intersections, overlapping parts, holes
        that cross the shell, etc.).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry. An empty ``Polygon`` is returned when the input
        encloses no area.
    """
    if isinstance(geom, Polygon):
        parts = [geom]
    elif isinstance(geom, MultiPolygon):
        parts = list(geom.geoms)
    else:
        raise TypeError(
            "fix_geometry expects a shapely Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )

    regions = [r for r in (_polygon_region(p) for p in parts) if not r.is_empty]
    if not regions:
        return Polygon()

    result = regions[0] if len(regions) == 1 else unary_union(regions)

    # Overlay operations produce valid output, but guard against any
    # numerical edge case by running make_valid as a last resort.
    if not result.is_valid:
        result = shapely.make_valid(result)

    return _assemble(_polygonal_parts(result))
```