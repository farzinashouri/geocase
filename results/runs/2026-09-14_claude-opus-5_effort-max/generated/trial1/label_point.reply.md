```python
"""Interior label points for polygons.

``label_point`` returns a polygon's *pole of inaccessibility*: the interior
point that is furthest from the boundary, holes included.  That is what a
cartographer wants under a label -- unlike the centroid it is always inside
the polygon, and unlike ``Polygon.representative_point`` it lands in the
middle of the widest part of the shape rather than wherever a scanline
happens to cross.

The search is Agafonkin's quadtree refinement ("polylabel"), run in the
polygon's own planar coordinates, so projected and geographic input are both
accepted.  Two caveats for lon/lat input: distances are measured in degrees,
so on tall polygons the point sits slightly poleward of the true geodesic
pole, and polygons crossing the antimeridian must be split before they get
here.
"""

from __future__ import annotations

import heapq
import itertools
from math import hypot, sqrt

import numpy as np
import shapely
from shapely import Point, Polygon

__all__ = ["label_point"]

_SQRT2 = sqrt(2.0)

# Default search precision, as a fraction of the bounding-box diagonal.  A
# relative tolerance is what makes "any coordinate system" work: an absolute
# one would be hopelessly coarse in degrees and pointlessly fine in
# millimetres.
_TOLERANCE_RATIO = 1e-4

# Cap on the number of cells used to seed the search.  A long thin polygon (a
# river, a panhandle) would otherwise start with max(w, h) / min(w, h) cells,
# which can run into the millions.  Any seeding that covers the bounding box
# is correct, so this only trades a coarser start for a bounded one.
_MAX_SEED_CELLS = 4096


def label_point(polygon: Polygon, *, tolerance: float | None = None) -> Point:
    """Return a point inside ``polygon`` at which to draw its label.

    Parameters
    ----------
    polygon:
        Polygon to label, in any coordinate system.  Invalid polygons are
        repaired with :func:`shapely.make_valid` and the largest resulting
        piece is labelled.
    tolerance:
        Search precision, in the polygon's own units.  Defaults to 1e-4 of
        the bounding-box diagonal.

    Returns
    -------
    Point
        A point lying inside ``polygon``.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If ``polygon`` is empty or encloses no area -- it then has no
        interior to put a label in -- or if ``tolerance`` is not positive.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    poly = _repaired(polygon)
    minx, miny, maxx, maxy = poly.bounds

    if tolerance is None:
        tolerance = hypot(maxx - minx, maxy - miny) * _TOLERANCE_RATIO
    elif not tolerance > 0:
        raise ValueError(f"tolerance must be positive, got {tolerance!r}")

    shapely.prepare(poly)  # caches a prepared geometry for the contains tests
    candidate = _pole_of_inaccessibility(poly, tolerance)

    # The search stops once it is within `tolerance` of the optimum, so on a
    # shape whose widest part is thinner than that it can come up just short
    # of the interior.  Fall back to a point GEOS guarantees is inside.
    for point in (candidate, poly.representative_point(), poly.centroid):
        if shapely.contains(poly, point):
            return point
    raise ValueError("no interior point could be found; polygon is degenerate")


def _repaired(polygon: Polygon) -> Polygon:
    """Return a valid, positive-area polygon to run the search on."""
    if polygon.is_valid:
        candidate = polygon
    else:
        candidate = _largest_polygon(shapely.make_valid(polygon))
    if candidate is None or candidate.area <= 0.0:
        raise ValueError("polygon encloses no area, so it has no interior point")
    return candidate


def _largest_polygon(geometry) -> Polygon | None:
    """Largest ``Polygon`` anywhere within ``geometry``, or None if there is none."""
    if isinstance(geometry, Polygon):
        return None if geometry.is_empty else geometry
    largest = None
    for part in getattr(geometry, "geoms", ()):
        candidate = _largest_polygon(part)
        if candidate is not None and (largest is None or candidate.area > largest.area):
            largest = candidate
    return largest


def _pole_of_inaccessibility(polygon: Polygon, tolerance: float) -> Point:
    """Find the interior point furthest from the boundary, to within ``tolerance``.

    Cells covering the bounding box are refined best-first: the cell whose
    *best possible* interior distance is highest is always the one split next,
    which lets whole regions be discarded without ever looking inside them.
    """
    boundary = polygon.boundary
    minx, miny, maxx, maxy = polygon.bounds
    cell_size = _seed_cell_size(maxx - minx, maxy - miny)
    half = cell_size / 2.0

    tiebreak = itertools.count()
    queue: list[tuple] = []

    def push(xs: np.ndarray, ys: np.ndarray, half: float) -> None:
        for x, y, d in zip(xs, ys, _signed_distance(xs, ys, polygon, boundary)):
            # The cell's own centre is `d` from the boundary and nothing in it
            # is more than half a diagonal further away, so d + h * sqrt(2)
            # bounds every point it contains.  Negated: heapq pops minima.
            heapq.heappush(queue, (-(d + half * _SQRT2), next(tiebreak), x, y, half, d))

    grid_x, grid_y = np.meshgrid(
        np.arange(minx + half, maxx + half, cell_size),
        np.arange(miny + half, maxy + half, cell_size),
    )
    push(grid_x.ravel(), grid_y.ravel(), half)

    # The centroid is already the answer for convex-ish shapes, and seeding
    # with it gives the pruning bound something to work with immediately.
    centroid = polygon.centroid
    push(np.array([centroid.x]), np.array([centroid.y]), 0.0)

    best_x, best_y, best_d = centroid.x, centroid.y, -np.inf

    while queue:
        neg_bound, _, x, y, half, d = heapq.heappop(queue)
        if d > best_d:
            best_x, best_y, best_d = x, y, d
        if -neg_bound - best_d <= tolerance:
            # Cells pop in order of decreasing bound and `best_d` only grows,
            # so nothing left can beat the best by more than `tolerance`.
            # Draining the rest anyway costs no geometry work and can still
            # nudge the answer inside a sliver thinner than the tolerance.
            continue
        quarter = half / 2.0
        push(
            np.array([x - quarter, x + quarter, x - quarter, x + quarter]),
            np.array([y - quarter, y - quarter, y + quarter, y + quarter]),
            quarter,
        )

    return Point(float(best_x), float(best_y))


def _seed_cell_size(width: float, height: float) -> float:
    """Side length of the cells that seed the search, covering the bounding box."""
    cell_size = min(width, height)
    if cell_size <= 0.0:  # a flat bounding box has no interior to grid
        raise ValueError("polygon encloses no area, so it has no interior point")
    cells = max(1.0, width / cell_size) * max(1.0, height / cell_size)
    if cells > _MAX_SEED_CELLS:
        cell_size *= sqrt(cells / _MAX_SEED_CELLS)
    return cell_size


def _signed_distance(
    xs: np.ndarray, ys: np.ndarray, polygon: Polygon, boundary
) -> np.ndarray:
    """Distance from each point to the nearest ring, negated outside the polygon.

    Measuring against the whole boundary rather than just the exterior ring is
    what keeps labels out of holes.
    """
    points = shapely.points(xs, ys)
    distances = shapely.distance(points, boundary)
    return np.where(shapely.contains(polygon, points), distances, -distances)
```