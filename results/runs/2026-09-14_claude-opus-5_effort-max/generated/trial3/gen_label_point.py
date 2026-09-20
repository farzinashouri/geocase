"""Pick a point inside a polygon that a map label can be anchored to.

The module exposes a single function, :func:`label_point`.
"""

from __future__ import annotations

import heapq
import itertools
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon

__all__ = ["label_point"]

# The search stops once the best candidate is within this fraction of the
# polygon's bounding-box size of the true optimum.  A shapely geometry carries
# no CRS, so precision has to be expressed relative to the polygon itself: an
# absolute tolerance would be meaningless in degrees and arbitrary in metres.
_RELATIVE_TOLERANCE = 1e-3

# Upper bound on the initial grid, so that a very long, thin polygon (aspect
# ratios of 10^5 are normal for rivers and road buffers) does not seed a huge
# queue.  Coarser seeding costs nothing in accuracy: the refinement loop only
# ever discards a cell that provably cannot hold a better answer.
_MAX_SEED_CELLS = 1024

# Hard stop for the refinement loop.  Not reached for realistic input; it just
# keeps pathological geometry from turning into a hang.
_MAX_REFINEMENTS = 100_000


class _Cell:
    """A square of the search grid, scored by the distance at its centre."""

    __slots__ = ("x", "y", "half", "distance", "bound")

    def __init__(self, x: float, y: float, half: float, distance: float) -> None:
        self.x = x
        self.y = y
        self.half = half
        # Signed distance to the boundary, positive inside the polygon.
        self.distance = distance
        # Signed distance is 1-Lipschitz, so no point of this cell can beat
        # the centre by more than the distance to a corner.
        self.bound = distance + half * math.sqrt(2.0)


def label_point(polygon: Polygon) -> Point:
    """Return a point inside ``polygon`` suitable for drawing a label at.

    The point is the polygon's *pole of inaccessibility*: the interior point
    furthest from the boundary (Mapbox's ``polylabel`` algorithm).  That beats
    the centroid, which falls outside a concave polygon and inside the hole of
    a ring-shaped one, and it beats
    :meth:`~shapely.Polygon.representative_point`, which is guaranteed to be
    inside but is usually hard up against an edge.

    The result always satisfies ``polygon.contains(result)`` and is always 2D,
    even for a polygon with Z coordinates.

    Coordinates are treated as planar and the point is returned in the
    polygon's own coordinate system; nothing is reprojected, because a shapely
    geometry does not record a CRS.  For geographic coordinates that means the
    pole of the lon/lat *plot* rather than of the shape on the sphere -- close
    enough to anchor a label, and still inside the polygon as drawn.

    An invalid polygon (self-intersecting, badly nested rings) is repaired with
    :func:`shapely.make_valid` first and the label is placed in the largest
    polygonal piece of the repair.

    Raises:
        TypeError: if ``polygon`` is not a shapely :class:`~shapely.Polygon`.
        ValueError: if the polygon is empty, has non-finite coordinates, or
            encloses no area, so that no point can lie inside it.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot place a label inside an empty polygon")
    if not all(math.isfinite(value) for value in polygon.bounds):
        raise ValueError("polygon has non-finite coordinates")

    working = polygon if polygon.is_valid else _largest_polygonal_part(polygon)
    if working.area <= 0.0:
        raise ValueError("polygon encloses no area, so no point lies inside it")

    return _pole_of_inaccessibility(working)


def _largest_polygonal_part(polygon: Polygon) -> Polygon:
    """Repair an invalid polygon and return its biggest polygonal piece."""
    parts = _polygonal_parts(shapely.make_valid(polygon))
    if not parts:
        raise ValueError("polygon encloses no area, so no point lies inside it")
    return max(parts, key=lambda part: part.area)


def _polygonal_parts(geometry) -> list[Polygon]:
    """Flatten any geometry down to its non-empty polygons."""
    if isinstance(geometry, Polygon):
        return [] if geometry.is_empty else [geometry]
    return [
        part
        for member in getattr(geometry, "geoms", ())
        for part in _polygonal_parts(member)
    ]


def _pole_of_inaccessibility(polygon: Polygon) -> Point:
    minx, miny, maxx, maxy = polygon.bounds
    width, height = maxx - minx, maxy - miny
    tolerance = max(width, height) * _RELATIVE_TOLERANCE

    # Prepared geometry makes the many point-in-polygon tests below cheap.  The
    # cache lives on the geometry and changes no observable behaviour.
    shapely.prepare(polygon)
    # For a polygon with holes this is exterior + interiors, so cells sitting
    # near a hole are scored against the hole's edge, as they should be.
    boundary = polygon.boundary

    # Seed with a point GEOS guarantees to be inside, so every candidate from
    # here on is already a legal answer and the search can only improve it.
    seed = polygon.representative_point()
    best = _cells([seed.x], [seed.y], 0.0, polygon, boundary)[0]
    if best.distance <= 0.0:
        raise ValueError("polygon is degenerate: no point lies strictly inside it")

    cell_size = _seed_cell_size(width, height)
    half = cell_size / 2.0
    # Cells are laid out from the low corner so their union covers the bounds.
    grid_x, grid_y = np.meshgrid(
        np.arange(minx, maxx, cell_size) + half,
        np.arange(miny, maxy, cell_size) + half,
    )

    queue: list[tuple[float, int, _Cell]] = []
    tiebreaker = itertools.count()
    for cell in _cells(grid_x.ravel(), grid_y.ravel(), half, polygon, boundary):
        if cell.distance > best.distance:
            best = cell
        heapq.heappush(queue, (-cell.bound, next(tiebreaker), cell))

    for _ in range(_MAX_REFINEMENTS):
        if not queue:
            break
        _, _, cell = heapq.heappop(queue)
        # The queue is ordered by the best score any point of a cell could
        # reach, so once the head cannot beat `best` by more than the
        # tolerance, neither can anything behind it.
        if cell.bound - best.distance <= tolerance:
            break

        half = cell.half / 2.0
        quadrant_x = (cell.x - half, cell.x + half, cell.x - half, cell.x + half)
        quadrant_y = (cell.y - half, cell.y - half, cell.y + half, cell.y + half)
        for child in _cells(quadrant_x, quadrant_y, half, polygon, boundary):
            if child.distance > best.distance:
                best = child
            if child.bound - best.distance > tolerance:
                heapq.heappush(queue, (-child.bound, next(tiebreaker), child))

    label = Point(best.x, best.y)
    # `best` is only ever replaced by a centre that tested inside, so this
    # holds by construction; check it anyway rather than risk returning an
    # outside point, and fall back to the seed, which GEOS vouches for.
    if not polygon.contains(label):
        return Point(seed.x, seed.y)
    return label


def _seed_cell_size(width: float, height: float) -> float:
    """Square-cell size for the initial grid, capped at _MAX_SEED_CELLS cells."""
    cell_size = min(width, height)
    count = math.ceil(width / cell_size) * math.ceil(height / cell_size)
    if count > _MAX_SEED_CELLS:
        cell_size *= math.sqrt(count / _MAX_SEED_CELLS)
    return cell_size


def _cells(xs, ys, half: float, polygon: Polygon, boundary) -> list[_Cell]:
    """Build cells centred on ``xs``/``ys``, signing distances inside-positive."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    distances = shapely.distance(shapely.points(xs, ys), boundary)
    inside = shapely.contains_xy(polygon, xs, ys)
    return [
        _Cell(float(x), float(y), half, float(distance if is_inside else -distance))
        for x, y, distance, is_inside in zip(xs, ys, distances, inside)
    ]