```python
from shapely.geometry import Polygon, Point

def label_point(polygon: Polygon) -> Point:
    """
    Return a point guaranteed to lie inside the given polygon, suitable for placing a text label.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which a label point is needed.

    Returns
    -------
    shapely.geometry.Point
        A point inside the polygon (the polygon's representative point).
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("Expected a shapely Polygon object")

    # representative_point() returns a point on the polygon's surface (always within the polygon)
    return polygon.representative_point()
```