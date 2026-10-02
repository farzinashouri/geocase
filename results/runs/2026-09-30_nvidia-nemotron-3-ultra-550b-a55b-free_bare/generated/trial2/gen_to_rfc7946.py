import pyproj
from shapely import ops as shapely_ops


def _to_lists(obj):
    """Recursively convert tuples to lists for JSON compatibility."""
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, list):
        return [_to_lists(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_lists(v) for k, v in obj.items()}
    return obj


def to_rfc7946(geom, epsg):
    """
    Convert a Shapely geometry to a RFC 7946 compliant GeoJSON geometry dict.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        Input geometry in the coordinate reference system identified by `epsg`.
    epsg : int
        EPSG code of the input geometry's CRS.

    Returns
    -------
    dict
        A GeoJSON geometry object (type + coordinates/geometries) with coordinates
        in WGS84 longitude/latitude order (EPSG:4326) and polygon rings oriented
        per the right-hand rule (exterior counterclockwise, interior clockwise).
    """
    # Create transformer from source CRS to WGS84 (EPSG:4326) with (x, y) = (lon, lat) order.
    source_crs = pyproj.CRS.from_epsg(epsg)
    target_crs = pyproj.CRS.from_epsg(4326)
    transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)

    def _transform_func(x, y, z=None):
        if z is None:
            return transformer.transform(x, y)
        return transformer.transform(x, y, z)

    # Reproject geometry to WGS84.
    geom_wgs84 = shapely_ops.transform(_transform_func, geom)

    # Orient polygon rings according to RFC 7946 (right-hand rule).
    geom_oriented = shapely_ops.orient(geom_wgs84, sign=1.0)

    # Convert to GeoJSON-like dict and ensure coordinates are lists (not tuples).
    geojson_dict = geom_oriented.__geo_interface__
    return _to_lists(geojson_dict)