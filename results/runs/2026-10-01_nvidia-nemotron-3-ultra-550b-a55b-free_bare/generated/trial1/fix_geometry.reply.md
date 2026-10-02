```python
"""Module for fixing invalid polygon geometries."""

from shapely import make_valid
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry


def fix_geometry(geom: BaseGeometry) -> Polygon | MultiPolygon:
    """
    Return a valid Polygon or MultiPolygon covering exactly the region enclosed by the input's boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which may be invalid (e.g., self-intersecting).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry representing the same region as the input. If the input is already valid,
        it is returned unchanged (or an equivalent normalized geometry).
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("Input must be a Polygon or MultiPolygon")

    if geom.is_valid:
        return geom

    fixed = make_valid(geom)

    # make_valid should return a Polygon or MultiPolygon for Polygon/MultiPolygon input.
    # Handle unexpected GeometryCollection by extracting polygonal parts.
    if fixed.geom_type == "GeometryCollection":
        polygons = []
        for part in fixed.geoms:
            if part.geom_type == "Polygon":
                polygons.append(part)
            elif part.geom_type == "MultiPolygon":
                polygons.extend(part.geoms)
        if not polygons:
            return Polygon()
        if len(polygons) == 1:
            return polygons[0]
        return MultiPolygon(polygons)

    if fixed.geom_type not in ("Polygon", "MultiPolygon"):
        # Fallback (should not occur for valid Polygon/MultiPolygon input)
        return Polygon()

    return fixed


__all__ = ["fix_geometry"]
```