"""
Module for buffering Shapely geometries in EPSG:4326 by a distance in meters.
"""

import pyproj
from shapely.geometry import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    The geometry is projected to an Azimuthal Equidistant projection centered
    on its centroid, buffered in meters, and then projected back to EPSG:4326.
    This provides accurate buffering anywhere on Earth for reasonably sized geometries.

    Parameters
    ----------
    geom : BaseGeometry
        Input geometry with coordinates in EPSG:4326 (longitude, latitude).
    distance_m : float
        Buffer distance in meters. Can be positive (expansion), negative (contraction),
        or zero (returns original geometry).

    Returns
    -------
    BaseGeometry
        Buffered geometry in EPSG:4326.
    """
    if geom.is_empty or distance_m == 0:
        return geom

    # Centroid of the geometry in geographic coordinates
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Azimuthal Equidistant projection centered on the centroid
    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    wgs84_crs = pyproj.CRS.from_epsg(4326)

    # Transformers (always_xy=True ensures (lon, lat) order)
    to_aeqd = pyproj.Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True).transform

    # Project to metric projection, buffer, project back
    geom_metric = transform(to_aeqd, geom)
    buffered_metric = geom_metric.buffer(distance_m)
    buffered_geographic = transform(to_wgs84, buffered_metric)

    return buffered_geographic


__all__ = ["buffer_m"]