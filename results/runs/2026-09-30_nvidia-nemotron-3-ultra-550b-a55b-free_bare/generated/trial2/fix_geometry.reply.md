```python
"""Module for fixing invalid polygon geometries."""

from shapely.geometry import Polygon, MultiPolygon


def fix_geometry(geom):
    """
    Return a valid Polygon or MultiPolygon covering exactly the region enclosed by the input's boundary rings.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which may be invalid (e.g., self-intersecting).

    Returns
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        A valid geometry representing the same region as the input's boundary.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("Input must be a Polygon or MultiPolygon")

    # `make_valid` (requires shapely >= 2.0) repairs the geometry while preserving
    # the point set defined by its boundary rings. It returns a Polygon or MultiPolygon.
    return geom.make_valid()


if __name__ == "__main__":
    # Simple sanity checks (no side effects on import)
    from shapely.geometry import Polygon, MultiPolygon

    # Valid polygon -> should return equivalent geometry
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    fixed = fix_geometry(poly)
    assert fixed.equals(poly)
    assert isinstance(fixed, Polygon)

    # Self-intersecting polygon (bow-tie)
    invalid = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    fixed = fix_geometry(invalid)
    assert fixed.is_valid
    assert isinstance(fixed, (Polygon, MultiPolygon))

    # MultiPolygon with one invalid part
    multi = MultiPolygon([poly, invalid])
    fixed_multi = fix_geometry(multi)
    assert fixed_multi.is_valid
    assert isinstance(fixed_multi, (Polygon, MultiPolygon))

    print("All basic tests passed.")
```