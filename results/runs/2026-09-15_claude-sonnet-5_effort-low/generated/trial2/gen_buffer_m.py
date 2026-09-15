"""Buffer WGS84 geometries by a distance in meters using a local azimuthal projection."""

from functools import partial

import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    aeqd = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        "+ellps=WGS84 +units=m +no_defs"
    )
    wgs84 = pyproj.CRS.from_epsg(4326)

    to_aeqd = pyproj.Transformer.from_crs(wgs84, aeqd, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(aeqd, wgs84, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)