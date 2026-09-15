```python
"""Compute the bounding box of a GeoJSON file's geometries in EPSG:4326."""

import json

from shapely.geometry import shape


def geojson_bounds(path):
    """Return (min_lon, min_lat, max_lon, max_lat) covering all features in path."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    geometries = []

    def collect(obj):
        if obj is None:
            return
        obj_type = obj.get("type")
        if obj_type == "FeatureCollection":
            for feature in obj.get("features", []):
                collect(feature)
        elif obj_type == "Feature":
            collect(obj.get("geometry"))
        elif obj_type == "GeometryCollection":
            for geom in obj.get("geometries", []):
                collect(geom)
        else:
            geometries.append(shape(obj))

    collect(data)

    if not geometries:
        raise ValueError(f"No geometries found in {path!r}")

    min_lon = min(g.bounds[0] for g in geometries)
    min_lat = min(g.bounds[1] for g in geometries)
    max_lon = max(g.bounds[2] for g in geometries)
    max_lat = max(g.bounds[3] for g in geometries)

    min_lon = max(min_lon, -180.0)
    max_lon = min(max_lon, 180.0)

    return (min_lon, min_lat, max_lon, max_lat)
```