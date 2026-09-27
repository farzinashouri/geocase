```python
"""Compute the WGS84 bounding box of a GeoJSON file.

Importing this module has no side effects.
"""

import json


def _iter_coords(node):
    """Yield (lon, lat) pairs from an arbitrarily nested coordinate array.

    A GeoJSON position is a list whose first two entries are lon, lat
    (optionally followed by elevation/other values); anything else is a
    nesting level to recurse into.
    """
    if not isinstance(node, (list, tuple)) or not node:
        return
    first = node[0]
    if isinstance(first, (int, float)) and len(node) >= 2 \
            and isinstance(node[1], (int, float)):
        yield float(node[0]), float(node[1])
    else:
        for child in node:
            yield from _iter_coords(child)


def _iter_geometries(obj):
    """Yield every geometry dict contained in a GeoJSON object."""
    if not isinstance(obj, dict):
        return
    kind = obj.get("type")
    if kind == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _iter_geometries(feature)
    elif kind == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif kind == "GeometryCollection":
        for geom in obj.get("geometries") or []:
            yield from _iter_geometries(geom)
    elif kind is not None and "coordinates" in obj:
        yield obj


def geojson_bounds(path):
    """Return (min_lon, min_lat, max_lon, max_lat) for a GeoJSON file.

    Coordinates are assumed to be lon/lat in EPSG:4326 (WGS84). The
    returned longitudes are normalized into [-180, 180].
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    lons = []
    lats = []
    for geom in _iter_geometries(data):
        for lon, lat in _iter_coords(geom.get("coordinates")):
            # Normalize longitude into [-180, 180].
            lon = ((lon + 180.0) % 360.0) - 180.0
            lons.append(lon)
            lats.append(lat)

    if not lons:
        raise ValueError("GeoJSON contains no coordinates")

    return (min(lons), min(lats), max(lons), max(lats))
```