import shapely
import shapely.ops
import shapely.geometry
import pyproj


def _transform_to_wgs84(geom: shapely.Geometry, epsg: int) -> shapely.Geometry:
    """Transform geometry to EPSG:4326 (WGS84) if not already in that CRS."""
    if epsg == 4326:
        return geom

    transformer = pyproj.Transformer.from_crs(epsg, 4326, always_xy=True)

    def _transform_coords(*coords):
        if len(coords) == 2:
            return transformer.transform(coords[0], coords[1])
        elif len(coords) == 3:
            x, y = transformer.transform(coords[0], coords[1])
            return (x, y, coords[2])
        else:
            raise ValueError(f"Unexpected coordinate dimension: {len(coords)}")

    return shapely.ops.transform(_transform_coords, geom)


def _orient_polygons(geom: shapely.Geometry) -> shapely.Geometry:
    """Ensure Polygon/MultiPolygon rings follow RFC 7946 winding order."""
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return shapely.orient(geom, sign=1.0)
    elif geom.geom_type == "GeometryCollection":
        return shapely.GeometryCollection([_orient_polygons(g) for g in geom.geoms])
    return geom


def to_rfc7946(geom: shapely.Geometry, epsg: int) -> dict:
    """
    Convert a Shapely geometry to a RFC 7946 compliant GeoJSON geometry dict.

    Parameters
    ----------
    geom : shapely.Geometry
        Input geometry in the coordinate reference system identified by `epsg`.
    epsg : int
        EPSG code of the input geometry's CRS (e.g., 4326, 3857).

    Returns
    -------
    dict
        GeoJSON geometry object with 'type' and 'coordinates' (and 'geometries' for GeometryCollection).
    """
    # Reproject to WGS84 (EPSG:4326) if necessary
    geom_wgs84 = _transform_to_wgs84(geom, epsg)

    # Make valid (fixes self-intersections, etc.) - may change geometry type
    geom_valid = shapely.make_valid(geom_wgs84)

    # Orient polygon rings per RFC 7946 (exterior CCW, interior CW)
    geom_oriented = _orient_polygons(geom_valid)

    # Convert to GeoJSON-like dict (type + coordinates)
    return shapely.geometry.mapping(geom_oriented)