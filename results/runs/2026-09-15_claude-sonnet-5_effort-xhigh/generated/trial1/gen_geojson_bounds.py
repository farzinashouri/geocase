"""Compute the bounding box of a GeoJSON file's geometries in EPSG:4326."""
import json

from shapely.geometry import shape


def _iter_geometries(obj):
    obj_type = obj.get("type")
    if obj_type == "FeatureCollection":
        for feature in obj.get("features", []):
            yield from _iter_geometries(feature)
    elif obj_type == "Feature":
        geometry = obj.get("geometry")
        if geometry is not None:
            yield from _iter_geometries(geometry)
    elif obj_type == "GeometryCollection":
        for geometry in obj.get("geometries", []):
            yield from _iter_geometries(geometry)
    else:
        yield obj


def geojson_bounds(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")

    for geometry in _iter_geometries(data):
        minx, miny, maxx, maxy = shape(geometry).bounds
        min_lon = min(min_lon, minx)
        min_lat = min(min_lat, miny)
        max_lon = max(max_lon, maxx)
        max_lat = max(max_lat, maxy)

    min_lon = max(min_lon, -180.0)
    max_lon = min(max_lon, 180.0)

    return (min_lon, min_lat, max_lon, max_lat)