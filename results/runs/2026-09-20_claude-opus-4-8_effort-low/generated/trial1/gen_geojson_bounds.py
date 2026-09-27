"""Compute the WGS84 bounding box of a GeoJSON file.

Coordinates are assumed to be longitude/latitude in EPSG:4326. The returned
box describes the actual extent of the geometry on Earth, with longitudes
constrained to [-180, 180].
"""

import json
import math


def _coords(geometry):
    """Yield (lon, lat) pairs from any GeoJSON geometry object."""
    if geometry is None:
        return
    gtype = geometry.get("type")
    if gtype == "GeometryCollection":
        for g in geometry.get("geometries", []):
            yield from _coords(g)
        return
    yield from _walk(geometry.get("coordinates"))


def _walk(coords):
    """Recursively yield (lon, lat) pairs from a nested coordinate array."""
    if not coords:
        return
    # A position is a flat list whose first element is a number.
    if isinstance(coords[0], (int, float)):
        yield float(coords[0]), float(coords[1])
        return
    for c in coords:
        yield from _walk(c)


def _features(obj):
    """Yield geometry objects from any top-level GeoJSON object."""
    gtype = obj.get("type")
    if gtype == "FeatureCollection":
        for feat in obj.get("features", []):
            if feat is not None:
                yield feat.get("geometry")
    elif gtype == "Feature":
        yield obj.get("geometry")
    else:
        yield obj


def _wrap(lon):
    """Normalize a longitude into [-180, 180]."""
    lon = math.fmod(lon, 360.0)
    if lon > 180.0:
        lon -= 360.0
    elif lon < -180.0:
        lon += 360.0
    return lon


def geojson_bounds(path):
    """Return (min_lon, min_lat, max_lon, max_lat) for a GeoJSON file.

    The bounding box reflects the true extent of the geometry. When the data
    spans the antimeridian, the tighter of the two candidate longitude spans
    (with/without wrapping) is chosen so the box describes the smaller real
    extent. All output longitudes lie within [-180, 180].
    """
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)

    lons = []
    lats = []
    for geometry in _features(obj):
        for lon, lat in _coords(geometry):
            lons.append(_wrap(lon))
            lats.append(lat)

    if not lons:
        raise ValueError("GeoJSON contains no coordinates")

    min_lat = min(lats)
    max_lat = max(lats)

    # Longitude extent: pick the smaller-span interval. The unwrapped span
    # goes from the westmost to eastmost point; the alternative wraps across
    # the antimeridian, using the largest gap between consecutive longitudes.
    ordered = sorted(set(lons))
    if len(ordered) == 1:
        return (ordered[0], min_lat, ordered[0], max_lat)

    plain_min, plain_max = ordered[0], ordered[-1]
    plain_span = plain_max - plain_min

    # Find the largest gap; wrapping across it yields the alternative box.
    gap = 0.0
    gap_idx = 0
    for i in range(len(ordered)):
        nxt = ordered[(i + 1) % len(ordered)]
        cur = ordered[i]
        diff = (nxt - cur) % 360.0
        if diff > gap:
            gap = diff
            gap_idx = i
    wrapped_span = 360.0 - gap

    if wrapped_span < plain_span:
        # Box crosses the antimeridian: west edge is just after the gap.
        min_lon = ordered[(gap_idx + 1) % len(ordered)]
        max_lon = ordered[gap_idx]
        return (min_lon, min_lat, max_lon, max_lat)

    return (plain_min, min_lat, plain_max, max_lat)