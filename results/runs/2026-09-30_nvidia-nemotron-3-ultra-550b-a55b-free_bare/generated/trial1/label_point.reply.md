```python
from shapely.geometry import Polygon, Point

def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the given polygon suitable for placing a text label.

    This uses Shapely's `representative_point()` method, which guarantees
    the returned point lies within the polygon (using GEOS's ST_PointOnSurface).

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon to label. Can be in any coordinate system.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to be inside the polygon.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("Expected a shapely Polygon object")
    return polygon.representative_point()
```