```python
"""Bounding box of a GeoJSON file in EPSG:4326, antimeridian-aware.

``geojson_bounds(path)`` returns ``(min_lon, min_lat, max_lon, max_lat)``.
Longitudes are normalised into ``[-180, 180]``.  Each segment between
consecutive vertices is taken along the shorter way round the globe, so a
feature crossing the antimeridian yields a box with ``min_lon > max_lon``
(as permitted by RFC 7946 §5.2) rather than one that spans the whole world.
"""

import json
import math


def _norm_lon(lon):
    """Wrap a longitude into [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def _iter_geometries(obj):
    """Yield every (non-collection) geometry object in a GeoJSON document."""
    if not isinstance(obj, dict):
        return
    t = obj.get("type")
    if t == "FeatureCollection":
        for f in obj.get("features") or []:
            yield from _iter_geometries(f)
    elif t == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif t == "GeometryCollection":
        for g in obj.get("geometries") or []:
            yield from _iter_geometries(g)
    elif t is not None:
        yield obj


def _iter_parts(geom):
    """Yield lists of positions, one per connected part (point, line, ring)."""
    t = geom.get("type")
    c = geom.get("coordinates")
    if c is None:
        return
    if t == "Point":
        yield [c]
    elif t in ("MultiPoint",):
        for p in c:
            yield [p]
    elif t == "LineString":
        yield c
    elif t in ("MultiLineString", "Polygon"):
        for part in c:
            yield part
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                yield ring


def _part_extent(part):
    """Return (lon_start, lon_length, min_lat, max_lat) for one part.

    Longitudes are unwrapped along the shortest route between consecutive
    vertices; the result is the covered arc on the circle of longitudes.
    """
    lo = hi = None
    min_lat = math.inf
    max_lat = -math.inf
    prev = None
    for pos in part:
        if not pos or len(pos) < 2:
            continue
        lon, lat = float(pos[0]), float(pos[1])
        if not (math.isfinite(lon) and math.isfinite(lat)):
            continue
        min_lat = min(min_lat, lat)
        max_lat = max(max_lat, lat)
        lon = _norm_lon(lon)
        if prev is None:
            cur = lon
        else:
            d = lon - _norm_lon(prev)
            if d > 180.0:
                d -= 360.0
            elif d <= -180.0:
                d += 360.0
            cur = prev + d
        prev = cur
        lo = cur if lo is None else min(lo, cur)
        hi = cur if hi is None else max(hi, cur)
    if lo is None:
        return None
    return _norm_lon(lo), hi - lo, min_lat, max_lat


def _merge_arcs(arcs):
    """Given (start, length) arcs on the longitude circle, return (west, east).

    Returns ``(-180.0, 180.0)`` when the arcs cover the whole circle.
    """
    linear = []
    for a, length in arcs:
        if length >= 360.0:
            return -180.0, 180.0
        linear.append((a, a + length))
        linear.append((a + 360.0, a + length + 360.0))
    linear.sort()
    merged = []
    for a, b in linear:
        if merged and a <= merged[-1][1]:
            if b > merged[-1][1]:
                merged[-1][1] = b
        else:
            merged.append([a, b])
    best_gap = 0.0
    best = None
    for i in range(len(merged) - 1):
        g0, g1 = merged[i][1], merged[i + 1][0]
        if g1 - g0 > best_gap:
            best_gap = g1 - g0
            best = (g0, g1)
    if best is None or best_gap <= 0.0:
        return -180.0, 180.0
    east, west = best
    west = _norm_lon(west)
    east = _norm_lon(east)
    if east == -180.0 and west != -180.0:
        east = 180.0
    return west, east


def geojson_bounds(path):
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Coordinates must be EPSG:4326 longitude/latitude.  Output longitudes are
    within ``[-180, 180]``; if the data crosses the antimeridian the box is
    expressed with ``min_lon > max_lon`` so it reflects the true extent.

    Raises ``ValueError`` if the file contains no usable coordinates.
    """
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    arcs = []
    min_lat = math.inf
    max_lat = -math.inf
    for geom in _iter_geometries(doc):
        for part in _iter_parts(geom):
            ext = _part_extent(part)
            if ext is None:
                continue
            start, length, plo, phi = ext
            arcs.append((start, length))
            min_lat = min(min_lat, plo)
            max_lat = max(max_lat, phi)

    if not arcs:
        raise ValueError(f"no coordinates found in {path!r}")

    west, east = _merge_arcs(arcs)
    min_lat = max(-90.0, min(90.0, min_lat))
    max_lat = max(-90.0, min(90.0, max_lat))
    return float(west), float(min_lat), float(east), float(max_lat)


__all__ = ["geojson_bounds"]
```