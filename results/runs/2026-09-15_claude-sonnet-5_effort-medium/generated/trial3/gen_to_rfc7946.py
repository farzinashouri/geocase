"""Convert shapely geometries to RFC 7946 compliant GeoJSON geometry dicts."""
from shapely.geometry import mapping
from shapely.geometry.polygon import orient
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from pyproj import Transformer


def _to_lists(coords):
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (int, float)):
            return list(coords[:2])
        return [_to_lists(c) for c in coords]
    return coords


def _orient_polygon(poly):
    return orient(poly, sign=1.0)


def _fix_winding(geom):
    gtype = geom.geom_type
    if gtype == "Polygon":
        return _orient_polygon(geom)
    if gtype == "MultiPolygon":
        from shapely.geometry import MultiPolygon
        return MultiPolygon([_orient_polygon(p) for p in geom.geoms])
    if gtype == "GeometryCollection":
        from shapely.geometry import GeometryCollection
        return GeometryCollection([_fix_winding(g) for g in geom.geoms])
    return geom


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    if epsg != 4326:
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        geom = shapely_transform(lambda x, y, z=None: transformer.transform(x, y), geom)

    geom = _fix_winding(geom)

    mapped = mapping(geom)

    if mapped["type"] == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [
                {"type": g["type"], "coordinates": _to_lists(g["coordinates"])}
                if g["type"] != "GeometryCollection"
                else g
                for g in mapped["geometries"]
            ],
        }

    return {"type": mapped["type"], "coordinates": _to_lists(mapped["coordinates"])}