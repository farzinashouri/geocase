"""Module for fixing invalid polygon geometries."""

from shapely import make_valid
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection


def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon by returning a valid geometry
    covering exactly the region enclosed by the input's boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which may be invalid (e.g., self-intersecting).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry representing the same region as the input's boundary.
        If the input is already valid, it is returned unchanged (or an equivalent
        valid representation).

    Raises
    ------
    TypeError
        If the input is not a Polygon or MultiPolygon.
    ValueError
        If the repair process produces an unexpected geometry type.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("Input must be a shapely Polygon or MultiPolygon")

    fixed = make_valid(geom)

    # For polygonal input, make_valid should return a Polygon or MultiPolygon.
    # Guard against unexpected GeometryCollection (e.g., if lower-dimensional
    # artifacts appear) by extracting polygonal parts.
    if isinstance(fixed, (Polygon, MultiPolygon)):
        return fixed

    if isinstance(fixed, GeometryCollection):
        polygonal_parts = [
            g for g in fixed.geoms if isinstance(g, (Polygon, MultiPolygon))
        ]
        if not polygonal_parts:
            raise ValueError("make_valid did not produce a polygonal geometry")
        if len(polygonal_parts) == 1:
            return polygonal_parts[0]
        return MultiPolygon(polygonal_parts)

    raise ValueError(f"make_valid produced unexpected geometry type: {type(fixed)}")