```python
"""
Module for computing the area of a shapely Polygon or MultiPolygon in square meters.
The input geometry must be in EPSG:4326 (longitude/latitude, WGS84).
"""

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform
from pyproj import Transformer


def area_m2(geom) -> float:
    """
    Return the area of a Polygon or MultiPolygon in square meters.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry in EPSG:4326 (lon/lat, WGS84).

    Returns
    -------
    float
        Area in square meters. Returns 0.0 for empty geometries.
    """
    if geom.is_empty:
        return 0.0

    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("geom must be a Polygon or MultiPolygon")

    # Centroid of the (multi)polygon in geographic coordinates
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    # Lambert Azimuthal Equal Area projection centered on the centroid
    laea_crs = (
        f"+proj=laea +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    transformer = Transformer.from_crs("EPSG:4326", laea_crs, always_xy=True)
    geom_projected = transform(transformer.transform, geom)

    return geom_projected.area
```