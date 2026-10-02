```python
import pyproj
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
)
from shapely import is_empty


def to_rfc7946(geom, epsg):
    """
    Convert a Shapely geometry to a GeoJSON geometry dict conforming to RFC 7946.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        The geometry to convert. Must not be empty.
    epsg : int
        The EPSG code of the coordinate reference system of the input geometry.

    Returns
    -------
    dict
        A GeoJSON geometry object with 'type' and 'coordinates' (or 'geometries' for GeometryCollection).
        Coordinates are in WGS 84 (EPSG:4326) with longitude, latitude order.
    """
    if is_empty(geom):
        raise ValueError("Empty geometries are not supported by RFC 7946")

    # Create a transformer from the source CRS to WGS 84 (EPSG:4326).
    # always_xy=True ensures the order is (x, y) i.e. (longitude, latitude) for 4326.
    transformer = pyproj.Transformer.from_crs(epsg, 4326, always_xy=True)

    def _transform_coords(coords):
        """Transform a sequence of (x, y) or (x, y, z) tuples to lists in target CRS."""
        transformed = []
        for coord in coords:
            if len(coord) == 2:
                x, y = transformer.transform(coord[0], coord[1])
                transformed.append([x, y])
            elif len(coord) == 3:
                x, y, z = transformer.transform(coord[0], coord[1], coord[2])
                transformed.append([x, y, z])
            else:
                raise ValueError(f"Unexpected coordinate dimension: {len(coord)}")
        return transformed

    def _process(geometry):
        gtype = geometry.geom_type

        if gtype == "Point":
            coords = list(geometry.coords)
            return {"type": "Point", "coordinates": _transform_coords(coords)[0]}

        elif gtype == "LineString":
            coords = list(geometry.coords)
            return {"type": "LineString", "coordinates": _transform_coords(coords)}

        elif gtype == "Polygon":
            exterior = list(geometry.exterior.coords)
            interiors = [list(interior.coords) for interior in geometry.interiors]
            return {
                "type": "Polygon",
                "coordinates": [_transform_coords(exterior)]
                + [_transform_coords(ring) for ring in interiors],
            }

        elif gtype == "MultiPoint":
            points = [list(g.coords)[0] for g in geometry.geoms]
            return {"type": "MultiPoint", "coordinates": _transform_coords(points)}

        elif gtype == "MultiLineString":
            lines = [list(g.coords) for g in geometry.geoms]
            return {
                "type": "MultiLineString",
                "coordinates": [_transform_coords(line) for line in lines],
            }

        elif gtype == "MultiPolygon":
            polygons = []
            for g in geometry.geoms:
                exterior = list(g.exterior.coords)
                interiors = [list(interior.coords) for interior in g.interiors]
                polygons.append(
                    [_transform_coords(exterior)]
                    + [_transform_coords(ring) for ring in interiors]
                )
            return {"type": "MultiPolygon", "coordinates": polygons}

        elif gtype == "GeometryCollection":
            return {
                "type": "GeometryCollection",
                "geometries": [_process(g) for g in geometry.geoms],
            }

        else:
            raise ValueError(f"Unsupported geometry type: {gtype}")

    return _process(geom)
```