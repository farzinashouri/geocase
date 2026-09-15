"""Bounding boxes for GeoJSON files in EPSG:4326.

The returned box describes the true extent of the geometry on the globe, so
geometry that spans the antimeridian yields a box whose ``min_lon`` is greater
than ``max_lon`` (the convention of RFC 7946 section 5.2).  All longitudes are
kept inside ``[-180, 180]``.
"""

import json

__all__ = ["geojson_bounds"]


def geojson_bounds(path):
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file."""
    with open(path, "r", encoding="utf-8") as handle:
        obj = json.load(handle)

    parts = []
    _collect(obj, parts)
    if not parts:
        raise ValueError("no coordinates found in %r" % (path,))

    lats = [lat for part in parts for _, lat in part]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = _lon_extent(parts)
    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))


def _collect(node, parts):
    """Append each coordinate sequence of ``node`` to ``parts``."""
    if not isinstance(node, dict):
        raise ValueError("expected a GeoJSON object")

    kind = node.get("type")
    if kind == "FeatureCollection":
        for feature in node.get("features") or []:
            _collect(feature, parts)
    elif kind == "Feature":
        geometry = node.get("geometry")
        if geometry is not None:
            _collect(geometry, parts)
    elif kind == "GeometryCollection":
        for geometry in node.get("geometries") or []:
            _collect(geometry, parts)
    elif kind in ("Point", "MultiPoint", "LineString", "MultiLineString",
                  "Polygon", "MultiPolygon"):
        coords = node.get("coordinates")
        if coords:
            _flatten(coords, 0 if kind == "Point" else _depth(kind), parts)
    else:
        raise ValueError("unsupported GeoJSON type %r" % (kind,))


def _depth(kind):
    """Nesting depth of lists above the individual positions."""
    return {
        "MultiPoint": 1,
        "LineString": 1,
        "MultiLineString": 2,
        "Polygon": 2,
        "MultiPolygon": 3,
    }[kind]


def _flatten(coords, depth, parts):
    """Split nested coordinates into flat lists of connected positions.

    A position sequence is kept together because consecutive vertices of a line
    or ring are what let us tell a short hop across the antimeridian from a long
    sweep the other way around the globe.
    """
    if depth == 0:
        parts.append([(float(coords[0]), float(coords[1]))])
    elif depth == 1:
        parts.append([(float(p[0]), float(p[1])) for p in coords])
    else:
        for child in coords:
            _flatten(child, depth - 1, parts)


def _wrap(lon):
    """Normalise a longitude into ``[-180, 180)``."""
    return (lon + 180.0) % 360.0 - 180.0


def _arc(part):
    """Longitude arc ``(start, length)`` covered by one position sequence.

    Longitudes are unwrapped so that every step between neighbouring vertices is
    the shorter of the two ways round; the arc is then the swept interval.
    """
    lons = [p[0] for p in part]
    unwrapped = [lons[0]]
    for lon in lons[1:]:
        previous = unwrapped[-1]
        unwrapped.append(previous + _wrap(lon - previous))
    low, high = min(unwrapped), max(unwrapped)
    return (_wrap(low), min(high - low, 360.0))


def _lon_extent(parts):
    """Smallest longitude interval on the circle containing every part."""
    segments = []
    for part in parts:
        start, length = _arc(part)
        if length >= 360.0:
            return (-180.0, 180.0)
        end = start + length
        if end > 180.0:
            segments.append((start, 180.0))
            segments.append((-180.0, end - 360.0))
        else:
            segments.append((start, end))

    segments.sort()
    merged = [segments[0]]
    for start, end in segments[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    # The bounding box is the complement of the widest uncovered gap.
    best_gap = 360.0 - (merged[-1][1] - merged[0][0])
    box = (merged[0][0], merged[-1][1])
    for index in range(len(merged) - 1):
        gap = merged[index + 1][0] - merged[index][1]
        if gap > best_gap:
            best_gap = gap
            box = (merged[index + 1][0], merged[index][1])
    return box