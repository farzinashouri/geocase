"""Compute the WGS84 bounding box of a GeoJSON file's geometry."""
import json


def _iter_coordinates(geometry):
    """Yield (lon, lat) pairs from any GeoJSON geometry object."""
    coords = geometry.get("coordinates")
    if coords is not None:
        yield from _iter_coordinate_tree(coords)
    else:
        for geom in geometry.get("geometries", []):
            yield from _iter_coordinates(geom)


def _iter_coordinate_tree(node):
    """Recursively walk a GeoJSON 'coordinates' array, yielding (lon, lat) pairs."""
    if not node:
        return
    if isinstance(node[0], (int, float)):
        yield node[0], node[1]
    else:
        for child in node:
            yield from _iter_coordinate_tree(child)


def _iter_geometries(obj):
    """Yield geometry dicts from a Feature, FeatureCollection, or bare geometry."""
    obj_type = obj.get("type")
    if obj_type == "FeatureCollection":
        for feature in obj.get("features", []):
            yield from _iter_geometries(feature)
    elif obj_type == "Feature":
        geometry = obj.get("geometry")
        if geometry is not None:
            yield from _iter_geometries(geometry)
    else:
        yield obj


def geojson_bounds(path):
    """Return (min_lon, min_lat, max_lon, max_lat) covering all features in the GeoJSON file at path."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")

    for geometry in _iter_geometries(data):
        for lon, lat in _iter_coordinates(geometry):
            if lon < min_lon:
                min_lon = lon
            if lon > max_lon:
                max_lon = lon
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat

    if min_lon == float("inf"):
        raise ValueError(f"No coordinates found in GeoJSON file: {path}")

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))