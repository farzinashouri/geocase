```python
"""Label placement for polygons.

:func:`label_point` returns a :class:`shapely.geometry.Point` that is verified
to lie in the interior of the polygon it is given, chosen so that it reads well
as the anchor for a text label.

The point it aims for is the *pole of inaccessibility*: the interior point that
is furthest from any edge, counting holes as edges.  That is a better label
anchor than the two obvious alternatives.  ``polygon.centroid`` is not
necessarily inside the polygon at all -- for a C-shape, a crescent or a ring it
falls in the notch or the hole -- and ``polygon.representative_point()``, while
always inside, is allowed to sit arbitrarily close to an edge, so labels
anchored there spill out of narrow shapes.

The function is coordinate-system agnostic: every length it uses internally is
derived from the polygon's own area, so it behaves identically whether the
input is in degrees, metres or feet, and the point it returns is in the input
coordinate system.  For geographic coordinates the result is the pole of
inaccessibility of the polygon *as drawn in lon/lat space*, which is not
exactly the geodesic one; it is still an interior point, which is what a
renderer needs.

Multipart input is labelled on its largest part, which is where the text has
room to go.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.validation import make_valid

try:  # shapely re-exports polylabel from shapely.ops; keep the real path as a
    from shapely.ops import polylabel as _polylabel  # backstop in case it moves
except ImportError:  # pragma: no cover - depends on shapely version
    try:
        from shapely.algorithms.polylabel import polylabel as _polylabel
    except ImportError:  # pragma: no cover - polylabel unavailable
        _polylabel = None

__all__ = ["label_point"]

# The pole of inaccessibility of a shape of area A has a clearance of at most
# sqrt(A / pi), so sizing the quadtree cut-off at sqrt(A) / 1000 keeps the
# search error three orders of magnitude below the quantity being maximised --
# far under a pixel for any sane label -- in whatever unit the polygon uses.
_TOLERANCE_FRACTION = 1e-3

# Each polylabel cell costs a full point-to-ring distance computation, so a
# coastline-detail polygon is much cheaper to search after simplification.  The
# shift this can introduce is invisible at label scale, and the resulting point
# is verified against the unsimplified polygon anyway.
_COARSEN_MIN_VERTICES = 1000
_COARSEN_FRACTION = 1e-4

# Heights (as a fraction of the bounding box) for the last-resort chord scan.
_SCANLINE_FRACTIONS = (0.5, 0.35, 0.65, 0.15, 0.85)


def label_point(polygon, *, tolerance=None):
    """Return a :class:`Point` inside ``polygon`` to draw its label at.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon or MultiPolygon
        Polygon in any coordinate system.  An invalid (e.g. self-intersecting)
        polygon is repaired first; a multipart polygon is labelled on its
        largest part.
    tolerance : float, optional
        Positive distance, in the polygon's own units, at which to stop
        refining the search.  Defaults to ``sqrt(area) / 1000``.  A larger
        value is faster and less precise.

    Returns
    -------
    shapely.geometry.Point
        A point for which ``polygon.contains(point)`` is true.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon`` or ``MultiPolygon``.
    ValueError
        If the polygon is empty, has non-finite coordinates, encloses no area,
        or if ``tolerance`` is not a finite positive number.  These are the
        cases where no interior point exists (or none can be found), so the
        function fails loudly rather than returning a point outside.
    """
    poly = _as_labelable_polygon(polygon)

    if tolerance is None:
        tolerance = math.sqrt(poly.area) * _TOLERANCE_FRACTION
        if not (math.isfinite(tolerance) and tolerance > 0):
            # A zero tolerance would make the quadtree refine forever; such a
            # degenerate scale falls through to the non-iterative candidates.
            tolerance = None
    elif not (math.isfinite(tolerance) and tolerance > 0):
        raise ValueError(
            f"tolerance must be a finite positive distance, got {tolerance!r}"
        )

    for candidate in _candidates(poly, tolerance):
        # contains() is the same predicate a caller would use to check the
        # result, and it is false on the boundary, so what we return is
        # strictly interior or we keep looking.
        if candidate is not None and not candidate.is_empty and poly.contains(candidate):
            return Point(candidate.x, candidate.y)

    raise ValueError("could not find an interior label point for this polygon")


def _candidates(poly, tolerance):
    """Yield label-point candidates best-first, computing each one lazily."""
    coarse = _coarsened(poly)
    if coarse is not None:
        yield _pole_of_inaccessibility(coarse, tolerance)
    yield _pole_of_inaccessibility(poly, tolerance)
    # Fallbacks, in decreasing order of how good they look under a label.
    yield poly.centroid
    yield poly.representative_point()
    yield _widest_chord_midpoint(poly)


def _as_labelable_polygon(poly):
    """Return the single valid, positive-area polygon to label."""
    if not isinstance(poly, (Polygon, MultiPolygon)):
        raise TypeError(
            f"label_point() expects a shapely Polygon, got {type(poly).__name__}"
        )
    if poly.is_empty:
        raise ValueError("label_point() cannot label an empty polygon")
    if not all(math.isfinite(bound) for bound in poly.bounds):
        raise ValueError(
            "label_point() cannot label a polygon with non-finite coordinates"
        )

    # A self-intersecting ring has no well-defined interior, so repair it rather
    # than asking GEOS predicates about it and trusting the answer.
    if not poly.is_valid:
        poly = make_valid(poly)

    largest = max(
        (part for part in _flatten(poly) if isinstance(part, Polygon) and part.area > 0),
        key=lambda part: part.area,
        default=None,
    )
    if largest is None:
        raise ValueError("label_point() cannot label a polygon that encloses no area")
    return largest


def _flatten(geom):
    """Yield the single-part geometries of ``geom``, skipping empty ones."""
    if geom.is_empty:
        return
    parts = getattr(geom, "geoms", None)
    if parts is None:
        yield geom
        return
    for part in parts:
        yield from _flatten(part)


def _coarsened(poly):
    """A cheaper stand-in for a very detailed polygon, or None to skip."""
    vertices = len(poly.exterior.coords) + sum(
        len(ring.coords) for ring in poly.interiors
    )
    if vertices < _COARSEN_MIN_VERTICES:
        return None
    coarse = poly.simplify(
        math.sqrt(poly.area) * _COARSEN_FRACTION, preserve_topology=True
    )
    if isinstance(coarse, Polygon) and coarse.area > 0 and coarse.is_valid:
        return coarse
    return None


def _pole_of_inaccessibility(poly, tolerance):
    """The interior point furthest from any edge, or None if unobtainable."""
    if _polylabel is None or tolerance is None:
        return None
    try:
        return _polylabel(poly, tolerance=tolerance)
    except Exception:
        # polylabel is a heuristic quadtree search that gives up on degenerate
        # rings; every caller of this has verified fallbacks behind it, so a
        # failure here is just a miss rather than an error.
        return None


def _widest_chord_midpoint(poly):
    """Midpoint of the widest horizontal chord, sampled at a few heights.

    Last resort for geometry the other candidates all failed on.  A chord of a
    positive-area polygon has its midpoint inside the polygon, and taking the
    widest one keeps that midpoint as far from the ends as the shape allows.
    """
    minx, miny, maxx, maxy = poly.bounds
    overhang = (maxx - minx) or 1.0
    best = None
    best_length = 0.0
    for fraction in _SCANLINE_FRACTIONS:
        y = miny + (maxy - miny) * fraction
        scanline = LineString([(minx - overhang, y), (maxx + overhang, y)])
        for part in _flatten(scanline.intersection(poly)):
            if isinstance(part, LineString) and part.length > best_length:
                best = part.interpolate(0.5, normalized=True)
                best_length = part.length
    return best
```