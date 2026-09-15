```python
"""Compute geodesic area (in square meters) of WGS84 lon/lat polygons."""

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

_GEOD = Geod(ellps="WGS84")


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area in square meters of a Polygon or MultiPolygon.

    Coordinates in `geom` are expected to be (longitude, latitude) pairs in
    EPSG:4326. Interior rings (holes) are subtracted automatically.
    """
    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    else:
        raise TypeError(
            f"area_m2 expects a Polygon or MultiPolygon, got {geom.geom_type!r}"
        )

    total = 0.0
    for polygon in polygons:
        area, _perimeter = _GEOD.geometry_area_perimeter(polygon)
        total += abs(area)

    return total
```