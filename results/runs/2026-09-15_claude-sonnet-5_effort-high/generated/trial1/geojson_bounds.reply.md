```python
"""Compute the WGS84 bounding box of a GeoJSON file, correctly handling
geometries that cross the antimeridian (+/-180 longitude)."""

import json


def _iter_positions(coords):
    """Yield (lon, lat) pairs from an arbitrarily nested GeoJSON coordinate array."""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        yield coords[0], coords[1]
    else:
        for item in coords:
            yield from _iter_positions(item)


def _iter_geometry_positions(geometry):
    if geometry is None:
        return
    gtype = geometry.get("type")
    if gtype == "GeometryCollection":
        for geom in geometry.get("geometries") or []:
            yield from _iter_geometry_positions(geom)
    else:
        coords = geometry.get("coordinates")
        if coords is not None:
            yield from _iter_positions(coords)


def _iter_object_positions(obj):
    otype = obj.get("type")
    if otype == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _iter_object_positions(feature)
    elif otype == "Feature":
        geometry = obj.get("geometry")
        if geometry is not None:
            yield from _iter_geometry_positions(geometry)
    else:
        yield from _iter_geometry_positions(obj)


def _smallest_enclosing_lon_arc(lons):
    """Return (min_lon, max_lon) for the smallest arc on the [-180, 180) circle
    containing all given longitudes. If the geometry crosses the antimeridian,
    min_lon will be greater than max_lon (per the RFC 7946 bbox convention)."""
    uniq = sorted(set(lons))
    n = len(uniq)
    if n == 1:
        return uniq[0], uniq[0]

    gaps = [(uniq[i + 1] - uniq[i], i) for i in range(n - 1)]
    gaps.append((uniq[0] + 360.0 - uniq[-1], n - 1))

    _, max_idx = max(gaps, key=lambda g: g[0])

    if max_idx == n - 1:
        return uniq[0], uniq[-1]
    return uniq[max_idx + 1], uniq[max_idx]


def geojson_bounds(path):
    """Return the (min_lon, min_lat, max_lon, max_lat) bounding box of every
    feature/geometry in the GeoJSON file at `path`.

    Longitudes are always within [-180, 180]. If the geometry's true extent
    crosses the antimeridian, min_lon will be greater than max_lon, matching
    the antimeridian-crossing bbox convention from RFC 7946 section 5.2.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lons = []
    lats = []
    for lon, lat in _iter_object_positions(data):
        lons.append(lon)
        lats.append(lat)

    if not lons:
        raise ValueError(f"No coordinates found in GeoJSON file: {path}")

    min_lat = min(lats)
    max_lat = max(lats)
    min_lon, max_lon = _smallest_enclosing_lon_arc(lons)

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```