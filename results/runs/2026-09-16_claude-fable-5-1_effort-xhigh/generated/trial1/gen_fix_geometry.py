"""Repair invalid polygonal geometries without changing the region they enclose.

The only public function is :func:`fix_geometry`.  It takes a shapely
``Polygon`` or ``MultiPolygon`` that may be invalid (self-crossing rings,
holes that poke outside their shell, overlapping or nested parts, ...) and
returns a valid ``Polygon``/``MultiPolygon`` covering exactly the region the
input's rings enclose:

* every shell ring is filled with the non-zero winding rule, so both lobes
  of a "bowtie" and the doubly-wound part of a self-overlapping loop stay
  covered;
* hole rings are filled the same way and then subtracted from their own
  shell only, so a hole that sticks out past its shell never turns into
  new area;
* the parts of a ``MultiPolygon`` are unioned, so overlapping or nested
  parts stay covered instead of cancelling out (as they would under the
  even-odd rule used by the default "linework" ``make_valid``).

The preferred engine is GEOS's structural ``make_valid`` (shapely >= 2.1
with GEOS >= 3.10), which implements exactly those rules.  When that is not
available, or fails, a pure noding + polygonize + winding-number fallback
is used.  Neither path relies on ``buffer(0)``, which silently drops one
lobe of a bowtie.
"""

from __future__ import annotations

from typing import Iterable, Iterator, List

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
from shapely.ops import polygonize, unary_union

__all__ = ["fix_geometry"]

_POLYGONAL_TYPES = ("Polygon", "MultiPolygon")


def fix_geometry(geom):
    """Return a valid Polygon/MultiPolygon covering exactly the region enclosed by ``geom``.

    Parameters
    ----------
    geom : shapely.Polygon or shapely.MultiPolygon
        Possibly invalid input.  A GeometryCollection made only of polygons
        is accepted too; anything else raises ``TypeError``.

    Returns
    -------
    shapely.Polygon or shapely.MultiPolygon
        Valid geometry.  An already-valid input is returned unchanged.  An
        input whose rings enclose no area (empty or fully collapsed) comes
        back as an empty ``Polygon``.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(
            "fix_geometry expects a shapely Polygon or MultiPolygon, got %s"
            % type(geom).__name__
        )
    if geom.is_empty:
        return Polygon()

    if geom.geom_type not in _POLYGONAL_TYPES:
        geom = _coerce_polygonal(geom)
        if geom.is_empty:
            return Polygon()

    if geom.is_valid:
        return geom

    fixed = None
    try:
        fixed = _as_polygonal(
            shapely.make_valid(geom, method="structure", keep_collapsed=False)
        )
    except Exception:
        # shapely < 2.1 / GEOS < 3.10 (no "structure" method), or a GEOS
        # failure on this particular input: fall back to our own engine.
        fixed = None

    if fixed is None or not fixed.is_valid:
        fixed = _as_polygonal(_fix_by_winding(geom))

    if not fixed.is_valid:
        # Last resort; the two engines above are expected to always yield
        # valid output, so this branch should be unreachable in practice.
        fixed = _as_polygonal(shapely.make_valid(fixed))

    return fixed


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _leaves(geom: BaseGeometry) -> Iterator[BaseGeometry]:
    """Yield the single-part geometries nested anywhere inside ``geom``."""
    if isinstance(geom, BaseMultipartGeometry):
        for part in geom.geoms:
            yield from _leaves(part)
    else:
        yield geom


def _polygons_in(geom: BaseGeometry) -> List[Polygon]:
    return [g for g in _leaves(geom) if g.geom_type == "Polygon" and not g.is_empty]


def _coerce_polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Turn a collection of polygons into a (Multi)Polygon; reject other content."""
    parts: List[Polygon] = []
    for part in _leaves(geom):
        if part.is_empty:
            continue
        if part.geom_type != "Polygon":
            raise TypeError(
                "fix_geometry expects polygonal input, found a %s inside a %s"
                % (part.geom_type, geom.geom_type)
            )
        parts.append(part)
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)


def _as_polygonal(geom) -> BaseGeometry:
    """Reduce any geometry to a Polygon/MultiPolygon made of its areal parts."""
    if geom is None or geom.is_empty:
        return Polygon()
    if geom.geom_type in _POLYGONAL_TYPES:
        return geom
    polys = _polygons_in(geom)
    if not polys:
        return Polygon()
    merged = unary_union(polys)
    if merged.is_empty:
        return Polygon()
    if merged.geom_type in _POLYGONAL_TYPES:
        return merged
    polys = _polygons_in(merged)
    if not polys:
        return Polygon()
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def _fix_by_winding(geom: BaseGeometry) -> BaseGeometry:
    """Structural repair: non-zero fill of each ring, holes subtracted, parts unioned."""
    pieces: List[BaseGeometry] = []
    for poly in _leaves(geom):
        if poly.geom_type != "Polygon" or poly.is_empty:
            continue
        shell = _fill_ring(poly.exterior.coords)
        if shell.is_empty:
            continue
        holes = [
            h for h in (_fill_ring(ring.coords) for ring in poly.interiors)
            if not h.is_empty
        ]
        if holes:
            shell = shell.difference(unary_union(holes))
        if not shell.is_empty:
            pieces.append(shell)
    if not pieces:
        return Polygon()
    return unary_union(pieces)


def _fill_ring(coords: Iterable) -> BaseGeometry:
    """Area enclosed by one (possibly self-intersecting) ring under the non-zero rule.

    The ring is fully noded, its faces are polygonized, and every face whose
    interior has a non-zero winding number with respect to the original ring
    is kept.  The kept faces are unioned into a valid Polygon/MultiPolygon.
    """
    xy = np.asarray(list(coords), dtype=float)
    if xy.ndim != 2 or xy.shape[0] == 0:
        return Polygon()
    xy = xy[:, :2]
    if not np.array_equal(xy[0], xy[-1]):
        xy = np.vstack([xy, xy[:1]])
    # Drop consecutive duplicate vertices; they add nothing to the boundary.
    keep = np.ones(len(xy), dtype=bool)
    keep[1:] = np.any(xy[1:] != xy[:-1], axis=1)
    xy = xy[keep]
    if len(xy) < 4:  # fewer than three distinct vertices: no area
        return Polygon()

    noded = unary_union(LineString(xy))  # fully nodes the self-intersections
    lines = list(noded.geoms) if isinstance(noded, BaseMultipartGeometry) else [noded]
    faces = [f for f in polygonize(lines) if not f.is_empty]
    if not faces:
        return Polygon()

    reps = [f.representative_point() for f in faces]
    px = np.array([p.x for p in reps], dtype=float)
    py = np.array([p.y for p in reps], dtype=float)
    winding = _winding_numbers(xy, px, py)

    kept = [f for f, w in zip(faces, winding) if w != 0]
    if not kept:
        return Polygon()
    return unary_union(kept)


def _winding_numbers(ring: np.ndarray, px: np.ndarray, py: np.ndarray) -> np.ndarray:
    """Winding number of each query point with respect to a closed ring (Sunday's algorithm)."""
    x0, y0 = ring[:-1, 0][:, None], ring[:-1, 1][:, None]
    x1, y1 = ring[1:, 0][:, None], ring[1:, 1][:, None]
    out = np.zeros(len(px), dtype=np.int64)
    n_edges = max(x0.shape[0], 1)
    step = max(1, 2_000_000 // n_edges)  # bound the edges x points work matrix
    for start in range(0, len(px), step):
        qx = px[start:start + step][None, :]
        qy = py[start:start + step][None, :]
        is_left = (x1 - x0) * (qy - y0) - (qx - x0) * (y1 - y0)
        upward = (y0 <= qy) & (y1 > qy) & (is_left > 0)
        downward = (y0 > qy) & (y1 <= qy) & (is_left < 0)
        out[start:start + step] = upward.sum(axis=0) - downward.sum(axis=0)
    return out