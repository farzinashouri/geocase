"""Module for fixing invalid polygon geometries."""

from shapely import make_valid
from shapely.geometry import Polygon, MultiPolygon


def fix_geometry(geom):
    """
    Return a valid geometry covering exactly the region enclosed by the input's boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which may be invalid (e.g., self-intersecting).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry representing the same region as the input.
        If the input is already valid, it is returned unchanged (or an equivalent copy).

    Raises
    ------
    TypeError
        If the input is not a Polygon or MultiPolygon.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("Input must be a Polygon or MultiPolygon")
    return make_valid(geom)