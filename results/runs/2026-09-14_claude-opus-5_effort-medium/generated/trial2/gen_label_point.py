"""Label-point computation for polygons.

The public entry point is :func:`label_point`, which returns a
:class:`shapely.Point` that is guaranteed to lie inside the polygon it is
given (for any polygon with non-zero area) and that is a good place to draw
a text label: it is the *pole of inaccessibility*, i.e. the interior point
that is furthest from the polygon boundary.

The centroid is not used directly because it can fall outside concave or
multi-part shapes (think of a "C"), and ``representative_point()`` is only
guaranteed to be inside -- it is often pressed right up against an edge.
The pole of inaccessibility is the point with the most free space around
it, which is what a label actually needs.

The search is the standard "polylabel" quadtree refinement (Vladimir
Agafonkin, 2016): start from a coarse grid over the bounding box, keep a
priority queue of cells ordered by the largest distance any point in the
cell could possibly have from the boundary, and repeatedly split the most
promising cell until no cell can beat the best point found so far by more
than ``tolerance``.

Everything is computed in the polygon's own planar coordinates.  The
function is therefore coordinate-system agnostic: feed it projected metres
and you get a point in metres, feed it lon/lat degrees and you get a point
in degrees.  (For lon/lat the notion of "furthest from the boundary" is
measured in degree space, which is mildly anisotropic away from the
equator, but the result is still a sensible, strictly interior label
anchor.)

Importing this module has no side effects.
"""

from __future__ import annotations

import heapq
import math
from itertools import count
from typing import Iterator, Optional, Tuple

import shapely
from shapely.geometry import MultiPolygon, Point, Polygon

__all__ = ["label_point"]


# Diagonal half-length factor: a square cell of half-size ``h`` extends at
# most ``h * SQRT2`` from its centre.
_SQRT2 = math.sqrt(2.0)

# Hard ceiling on quadtree refinement steps, so that a pathological input
# can never spin forever.  In practice convergence takes far fewer steps.
_MAX_ITERATIONS = 100_000


def label_point(polygon, tolerance: Optional[float] = None) -> Point:
    """Return a point inside ``polygon`` at which to draw its label.

    Parameters
    ----------
    polygon : shapely.Polygon or shapely.MultiPolygon
        The shape to label, in any coordinate system.  Invalid geometries
        (self-intersections, bowties) are repaired first; multi-part input
        is labelled on its largest part.
    tolerance : float, optional
        Absolute stopping tolerance in input coordinate units.  The
        returned point is within ``tolerance`` of the true pole of
        inaccessibility.  Defaults to 1/1000 of the larger bounding-box
        side, which is finer than a pixel for any realistic rendering.

    Returns
    -------
    shapely.Point
        A point that lies inside ``polygon``.  For a degenerate (zero-area)
        polygon, where no strictly interior point exists, a point on the
        geometry is returned instead.

    Raises
    ------
    TypeError
        If ``polygon`` is not a Polygon or MultiPolygon.
    ValueError
        If ``polygon`` is empty, has non-finite coordinates, or cannot be
        repaired into a polygonal geometry.
    """
    poly = _prepare_polygon(polygon)

    minx, miny, maxx, maxy = poly.bounds
    width = maxx - minx
    height = maxy - miny

    # Degenerate extent (a point, or a perfectly axis-aligned sliver):
    # there is nothing to search, so fall back to a guaranteed-on-geometry
    # point.
    if width <= 0.0 or height <= 0.0:
        return _fallback_point(poly)

    if tolerance is None:
        tolerance = max(width, height) / 1000.0
    elif tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    # ``contains_xy`` against a prepared geometry is what makes the inside
    # test cheap enough to run thousands of times.
    shapely.prepare(poly)
    boundary = poly.boundary

    cell_size = min(width, height)
    half = cell_size / 2.0

    # Ties in the priority queue are broken by an ever-increasing counter so
    # that heapq never has to compare two _Cell objects.
    tiebreak = count()
    queue: list = []

    def push(cell: "_Cell") -> None:
        # Negated: heapq is a min-heap, we want the largest potential first.
        heapq.heappush(queue, (-cell.potential, next(tiebreak), cell))

    for x, y in _grid_centres(minx, miny, maxx, maxy, cell_size):
        push(_make_cell(x, y, half, poly, boundary))

    # Seed the best-so-far with two cheap candidates.  The centroid is
    # usually excellent for convex shapes; the bbox centre is a harmless
    # backstop when the centroid lands in a hole.
    best = _make_cell(
        (minx + maxx) / 2.0, (miny + maxy) / 2.0, 0.0, poly, boundary
    )
    centroid = poly.centroid
    if not centroid.is_empty:
        candidate = _make_cell(centroid.x, centroid.y, 0.0, poly, boundary)
        if candidate.distance > best.distance:
            best = candidate

    iterations = 0
    while queue and iterations < _MAX_ITERATIONS:
        iterations += 1
        _, _, cell = heapq.heappop(queue)

        if cell.distance > best.distance:
            best = cell

        # No point in this cell can improve on ``best`` by more than the
        # tolerance, so neither can any of its descendants.
        if cell.potential - best.distance <= tolerance:
            continue

        quarter = cell.half / 2.0
        if quarter <= 0.0:
            continue
        for dx in (-quarter, quarter):
            for dy in (-quarter, quarter):
                push(
                    _make_cell(
                        cell.x + dx, cell.y + dy, quarter, poly, boundary
                    )
                )

    if best.distance <= 0.0:
        # Nothing strictly interior was found -- possible only for
        # zero-area or numerically pathological input.
        return _fallback_point(poly)

    point = Point(best.x, best.y)
    # Belt and braces: honour the contract literally, even if floating
    # point conspired against the search.
    if not poly.contains(point):
        return _fallback_point(poly)
    return point


class _Cell:
    """A square candidate region of the quadtree search."""

    __slots__ = ("x", "y", "half", "distance", "potential")

    def __init__(self, x: float, y: float, half: float, distance: float):
        self.x = x
        self.y = y
        self.half = half
        # Signed distance from the cell centre to the polygon boundary,
        # positive inside.
        self.distance = distance
        # Upper bound on the signed distance of any point in this cell.
        self.potential = distance + half * _SQRT2


def _make_cell(x: float, y: float, half: float, poly, boundary) -> _Cell:
    distance = shapely.distance(Point(x, y), boundary)
    if not shapely.contains_xy(poly, x, y):
        distance = -distance
    return _Cell(x, y, half, distance)


def _grid_centres(
    minx: float, miny: float, maxx: float, maxy: float, cell_size: float
) -> Iterator[Tuple[float, float]]:
    """Yield the centres of a ``cell_size`` grid covering the bounding box.

    The grid is one cell thick along the short axis, so the cell count is
    just the bounding box aspect ratio -- cheap even for long thin shapes.
    """
    half = cell_size / 2.0
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            yield x + half, y + half
            y += cell_size
        x += cell_size


def _prepare_polygon(polygon):
    """Validate, repair and reduce the input to a single usable Polygon."""
    if not isinstance(polygon, (Polygon, MultiPolygon)):
        raise TypeError(
            "label_point() expects a shapely Polygon or MultiPolygon, "
            f"got {type(polygon).__name__}"
        )
    if polygon.is_empty:
        raise ValueError("label_point() requires a non-empty polygon")

    bounds = polygon.bounds
    if not all(math.isfinite(value) for value in bounds):
        raise ValueError("polygon has non-finite coordinates")

    geom = polygon
    if not geom.is_valid:
        geom = shapely.make_valid(geom)

    geom = _largest_polygonal_part(geom)
    if geom is None or geom.is_empty:
        raise ValueError("polygon has no polygonal component to label")
    return geom


def _largest_polygonal_part(geom):
    """Return the highest-area Polygon inside ``geom``, or None."""
    if isinstance(geom, Polygon):
        return geom

    best = None
    best_area = -1.0
    # make_valid() can hand back a GeometryCollection mixing lines and
    # polygons; walk it and keep only the polygonal pieces.
    parts = list(getattr(geom, "geoms", ()))
    while parts:
        part = parts.pop()
        if isinstance(part, Polygon):
            if not part.is_empty and part.area > best_area:
                best, best_area = part, part.area
        elif hasattr(part, "geoms"):
            parts.extend(part.geoms)
    return best


def _fallback_point(geom) -> Point:
    """A guaranteed on-geometry point for degenerate inputs."""
    try:
        return geom.representative_point()
    except Exception:
        centroid = geom.centroid
        if not centroid.is_empty:
            return centroid
        minx, miny, maxx, maxy = geom.bounds
        return Point((minx + maxx) / 2.0, (miny + maxy) / 2.0)