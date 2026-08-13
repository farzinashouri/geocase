from shapely.geometry import mapping, MultiPolygon, GeometryCollection
from shapely.ops import transform
from shapely.geometry.polygon import orient
import pyproj


def to_rfc7946(geom, epsg):
    """
    Convert a Shapely geometry to a RFC 7946 compliant GeoJSON geometry dict.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        Input geometry in the coordinate reference system given by `epsg`.
    epsg : int
        EPSG code of the input geometry's CRS (e.g., 4326, 3857).

    Returns
    -------
    dict
        GeoJSON geometry object with 'type' and 'coordinates' members.
        Coordinates are in WGS84 (EPSG:4326) longitude/latitude order.
        Polygon rings are oriented per RFC 7946 (exterior counterclockwise,
        interiors clockwise).
    """
    # Reproject to WGS84 if necessary
    if epsg != 4326:
        transformer = pyproj.Transformer.from_crs(
            f"EPSG:{epsg}", "EPSG:4326", always_xy=True
        )
        geom = transform(transformer.transform, geom)

    # Ensure polygon ring orientation complies with RFC 7946
    def _orient(g):
        if g.geom_type == "Polygon":
            return orient(g, sign=1.0)  # exterior CCW, interiors CW
        elif g.geom_type == "MultiPolygon":
            return MultiPolygon([_orient(p) for p in g.geoms])
        elif g.geom_type == "GeometryCollection":
            return GeometryCollection([_orient(p) for p in g.geoms])
        return g

    geom = _orient(geom)

    # Convert to GeoJSON-like dict (type + coordinates)
    return mapping(geom)