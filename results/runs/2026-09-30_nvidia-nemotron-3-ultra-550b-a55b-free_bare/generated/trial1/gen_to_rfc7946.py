from shapely.geometry import mapping
from shapely.ops import transform
from pyproj import Transformer


def to_rfc7946(geom, epsg):
    """
    Convert a Shapely geometry to a GeoJSON geometry dict conforming to RFC 7946.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        The input geometry in the coordinate reference system given by `epsg`.
    epsg : int
        The EPSG code of the input geometry's CRS.

    Returns
    -------
    dict
        A GeoJSON geometry object with 'type' and 'coordinates' members,
        in WGS 84 (EPSG:4326) with longitude/latitude order.
    """
    if epsg != 4326:
        # Create a transformer from the source CRS to WGS 84 (EPSG:4326)
        # always_xy=True ensures the order is (x, y) i.e. (longitude, latitude)
        transformer = Transformer.from_crs(epsg, 4326, always_xy=True)
        geom = transform(transformer.transform, geom)

    # mapping returns a GeoJSON-like dict with 'type' and 'coordinates'
    return mapping(geom)