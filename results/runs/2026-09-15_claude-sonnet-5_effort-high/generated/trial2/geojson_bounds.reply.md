```python
"""Compute the WGS84 bounding box of a GeoJSON file's geometries."""

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
    """Return (min_lon, min_lat, max_lon, max_lat) for all geometries in a GeoJSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")

    for geom_dict in _iter_geometries(data):
        geom = shape(geom_dict)
        gmin_lon, gmin_lat, gmax_lon, gmax_lat = geom.bounds
        min_lon = min(min_lon, gmin_lon)
        min_lat = min(min_lat, gmin_lat)
        max_lon = max(max_lon, gmax_lon)
        max_lat = max(max_lat, gmax_lat)

    if min_lon == float("inf"):
        raise ValueError(f"No geometries found in {path!r}")

    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```