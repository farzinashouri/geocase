"""Compute a point inside a polygon suitable for drawing a text label.

Uses the pole of inaccessibility (the center of the polygon's maximum
inscribed circle), which is the point furthest from the boundary and so
gives a label the most room. Falls back to shapely's cheaper
``representative_point`` if that computation is unavailable or degenerate.
"""

from shapely.geometry import Point, Polygon

try:  # shapely >= 2.1
    from shapely import maximum_inscribed_circle as _max_inscribed_circle
except ImportError:  # pragma: no cover - older shapely
    _max_inscribed_circle = None

# Fraction of the polygon's diagonal used as the search tolerance. Small
# enough to be visually exact, large enough to keep the search cheap.
_TOLERANCE_RATIO = 1e-3


def label_point(polygon):
    """Return a shapely ``Point`` inside ``polygon`` at which to draw a label.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        Polygon in any coordinate system. May be invalid (self-intersecting);
        it is repaired before the label position is computed.

    Returns
    -------
    shapely.geometry.Point
        A point that lies inside ``polygon``.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If ``polygon`` is empty or has zero area, so no interior point exists.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    geom = polygon
    if not geom.is_valid:
        # buffer(0) resolves self-intersections; the result may be a
        # MultiPolygon, in which case label the largest part.
        geom = geom.buffer(0)
        if geom.is_empty:
            raise ValueError("cannot label a polygon with no valid interior")
        if geom.geom_type == "MultiPolygon":
            geom = max(geom.geoms, key=lambda part: part.area)
        elif geom.geom_type != "Polygon":
            raise ValueError("cannot label a polygon with no valid interior")

    if geom.area == 0.0:
        raise ValueError("cannot label a polygon with zero area")

    point = _pole_of_inaccessibility(geom)
    if point is not None and geom.contains(point):
        return point

    # representative_point is guaranteed to lie within the geometry.
    return geom.representative_point()


def _pole_of_inaccessibility(geom):
    """Center of ``geom``'s maximum inscribed circle, or None if unavailable."""
    if _max_inscribed_circle is None:
        return None

    minx, miny, maxx, maxy = geom.bounds
    diagonal = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    tolerance = diagonal * _TOLERANCE_RATIO
    if tolerance <= 0.0:
        return None

    try:
        radius_line = _max_inscribed_circle(geom, tolerance=tolerance)
    except Exception:
        # Degenerate geometry (slivers, near-duplicate vertices) can make the
        # GEOS routine fail; the caller falls back to representative_point.
        return None

    if radius_line.is_empty:
        return None
    return Point(radius_line.coords[0])