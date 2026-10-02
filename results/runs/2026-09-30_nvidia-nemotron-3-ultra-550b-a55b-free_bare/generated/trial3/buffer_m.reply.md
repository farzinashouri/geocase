```python
import pyproj
from shapely.geometry import BaseGeometry
from shapely.ops import transform

def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    The geometry is projected into a local Azimuthal Equidistant projection
    centered on its centroid, buffered, and then projected back to EPSG:4326.
    This provides accurate metric buffering anywhere on Earth.

    Parameters
    ----------
    geom : BaseGeometry
        Input geometry with coordinates in EPSG:4326 (longitude, latitude).
    distance_m : float
        Buffer distance in meters. Can be positive (expansion), negative (erosion),
        or zero (returns original geometry).

    Returns
    -------
    BaseGeometry
        Buffered geometry in EPSG:4326.
    """
    if geom.is_empty or distance_m == 0:
        return geom

    # Centroid in WGS84 (lon, lat)
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Custom Azimuthal Equidistant projection centered on the centroid
    proj_string = (
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    crs_custom = pyproj.CRS.from_proj4(proj_string)
    crs_wgs84 = pyproj.CRS.from_epsg(4326)

    # Transformers (always_xy=True keeps order as longitude, latitude / easting, northing)
    to_custom = pyproj.Transformer.from_crs(crs_wgs84, crs_custom, always_xy=True)
    to_wgs84 = pyproj.Transformer.from_crs(crs_custom, crs_wgs84, always_xy=True)

    def forward(x, y, z=None):
        if z is None:
            return to_custom.transform(x, y)
        return to_custom.transform(x, y, z)

    def inverse(x, y, z=None):
        if z is None:
            return to_wgs84.transform(x, y)
        return to_wgs84.transform(x, y, z)

    # Project to metric CRS, buffer, project back
    geom_metric = transform(forward, geom)
    geom_buffered = geom_metric.buffer(distance_m)
    geom_result = transform(inverse, geom_buffered)

    return geom_result
```