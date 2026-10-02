```python
import shapely.geometry
import shapely.ops
import pyproj


def _orient_polygons(geom):
    """Recursively orient all Polygon rings to RFC 7946 winding order."""
    if geom.is_empty:
        return geom
    gtype = geom.geom_type
    if gtype == "Polygon":
        # sign=1.0 -> exterior CCW, interiors CW
        return shapely.geometry.polygon.orient(geom, sign=1.0)
    if gtype == "MultiPolygon":
        return shapely.geometry.MultiPolygon([_orient_polygons(p) for p in geom.geoms])
    if gtype == "GeometryCollection":
        return shapely.geometry.GeometryCollection([_orient_polygons(g) for g in geom.geoms])
    return geom


def to_rfc7946(geom, epsg):
    """
    Convert a Shapely geometry to a RFC 7946 compliant GeoJSON geometry dict.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        Input geometry in the CRS identified by `epsg`.
    epsg : int
        EPSG code of the input geometry's CRS.

    Returns
    -------
    dict
        GeoJSON geometry object with 'type' and 'coordinates' members.
    """
    # Transform to WGS84 (EPSG:4326) if necessary
    if epsg != 4326:
        transformer = pyproj.Transformer.from_crs(
            f"EPSG:{epsg}", "EPSG:4326", always_xy=True
        )
        geom = shapely.ops.transform(transformer.transform, geom)

    # Ensure correct polygon winding order
    geom = _orient_polygons(geom)

    # Convert to GeoJSON-like dict (type + coordinates)
    return shapely.geometry.mapping(geom)
```