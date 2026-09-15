"""Buffer WGS84 geometries by a distance in meters using a local azimuthal projection."""

from functools import partial

from pyproj import CRS, Transformer
from shapely.ops import transform


def buffer_m(geom, distance_m):
    lon, lat = geom.centroid.x, geom.centroid.y

    aeqd_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    )
    wgs84_crs = CRS.from_epsg(4326)

    to_aeqd = Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True).transform

    projected_geom = transform(to_aeqd, geom)
    buffered_geom = projected_geom.buffer(distance_m)

    return transform(to_wgs84, buffered_geom)