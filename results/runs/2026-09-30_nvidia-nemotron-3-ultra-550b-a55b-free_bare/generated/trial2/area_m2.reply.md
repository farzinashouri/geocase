```python
from pyproj import Geod
from shapely.geometry import Polygon, MultiPolygon

# Geod instance for WGS84 ellipsoid (EPSG:4326)
_GEOD = Geod(ellps="WGS84")

def area_m2(geom):
    """
    Return the area of a shapely Polygon or MultiPolygon in square meters.

    The input geometry must be in EPSG:4326 (longitude/latitude).
    The calculation uses geodesic algorithms on the WGS84 ellipsoid,
    so it is accurate for polygons anywhere on Earth.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry in EPSG:4326.

    Returns
    -------
    float
        Area in square meters. Returns 0.0 for empty geometries.
    """
    if geom.is_empty:
        return 0.0

    # pyproj's geometry_area_perimeter returns (area, perimeter) in meters.
    # The area is signed (positive for exterior rings, negative for holes);
    # we take the absolute value to get the total area.
    area, _ = _GEOD.geometry_area_perimeter(geom)
    return abs(area)
```