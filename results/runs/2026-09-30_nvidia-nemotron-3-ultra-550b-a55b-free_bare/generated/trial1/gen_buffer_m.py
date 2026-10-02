from shapely.geometry import BaseGeometry
from shapely.ops import transform
import pyproj


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        Input geometry in WGS84 (EPSG:4326) coordinates (longitude, latitude).
    distance_m : float
        Buffer distance in meters.

    Returns
    -------
    shapely.geometry.BaseGeometry
        Buffered geometry in EPSG:4326.
    """
    if geom.is_empty or distance_m == 0:
        return geom

    # Centroid of the input geometry (in degrees)
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Azimuthal equidistant projection centered on the centroid
    proj_str = (
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    custom_crs = pyproj.CRS.from_proj4(proj_str)
    wgs84 = pyproj.CRS.from_epsg(4326)

    # Transformers (always_xy=True ensures (x, y) = (lon, lat) order)
    to_custom = pyproj.Transformer.from_crs(wgs84, custom_crs, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(custom_crs, wgs84, always_xy=True).transform

    # Project to metric CRS, buffer, project back
    geom_metric = transform(to_custom, geom)
    geom_buffered = geom_metric.buffer(distance_m)
    geom_result = transform(to_wgs84, geom_buffered)

    return geom_result