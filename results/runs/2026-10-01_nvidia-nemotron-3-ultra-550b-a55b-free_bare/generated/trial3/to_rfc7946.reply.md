```python
import pyproj
import shapely
import shapely.geometry
import shapely.ops


def _to_geojson(geom: shapely.Geometry) -> dict:
    """Convert a Shapely geometry (assumed to be in EPSG:4326, lon/lat order) to a RFC 7946 GeoJSON dict."""
    if geom.is_empty:
        raise ValueError("Empty geometries are not valid in RFC 7946")

    geom_type = geom.geom_type

    if geom_type == "Point":
        return {"type": "Point", "coordinates": list(geom.coords[0])}

    if geom_type == "MultiPoint":
        return {"type": "MultiPoint", "coordinates": [list(p.coords[0]) for p in geom.geoms]}

    if geom_type == "LineString":
        return {"type": "LineString", "coordinates": [list(c) for c in geom.coords]}

    if geom_type == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [[list(c) for c in ls.coords] for ls in geom.geoms],
        }

    if geom_type == "Polygon":
        # RFC 7946: exterior ring counterclockwise, interior rings clockwise
        oriented = shapely.geometry.polygon.orient(geom, sign=1.0)
        exterior = [list(c) for c in oriented.exterior.coords]
        interiors = [[list(c) for c in interior.coords] for interior in oriented.interiors]
        return {"type": "Polygon", "coordinates": [exterior] + interiors}

    if geom_type == "MultiPolygon":
        polygons = []
        for poly in geom.geoms:
            oriented = shapely.geometry.polygon.orient(poly, sign=1.0)
            exterior = [list(c) for c in oriented.exterior.coords]
            interiors = [[list(c) for c in interior.coords] for interior in oriented.interiors]
            polygons.append([exterior] + interiors)
        return {"type": "MultiPolygon", "coordinates": polygons}

    if geom_type == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_to_geojson(g) for g in geom.geoms],
        }

    raise TypeError(f"Unsupported geometry type: {geom_type}")


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
        A GeoJSON geometry object (with 'type' and 'coordinates'/'geometries')
        in WGS 84 (EPSG:4326) longitude/latitude order, with correct polygon winding.
    """
    # Transform to EPSG:4326 (WGS 84) with axis order (longitude, latitude)
    transformer = pyproj.Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    geom_4326 = shapely.ops.transform(transformer.transform, geom)
    return _to_geojson(geom_4326)
```