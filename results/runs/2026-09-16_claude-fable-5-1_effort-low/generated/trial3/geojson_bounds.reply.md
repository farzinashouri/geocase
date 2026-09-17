```python
"""Bounding box of a GeoJSON file in EPSG:4326, antimeridian-aware.

The returned box is ``(min_lon, min_lat, max_lon, max_lat)``.  When the
geometry genuinely straddles the antimeridian the box follows RFC 7946
section 5.2: ``min_lon`` (west) is numerically greater than ``max_lon``
(east), and both stay inside ``[-180, 180]``.
"""

import json
import math
from typing import Iterable, Iterator, List, Sequence, Tuple

Coord = Sequence[float]

_LINE_TYPES = {"LineString", "MultiLineString", "Polygon", "MultiPolygon"}


def _norm_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180] (180 stays 180)."""
    if -180.0 <= lon <= 180.0:
        return float(lon)
    lon = (float(lon) + 180.0) % 360.0 - 180.0
    return 180.0 if lon == -180.0 else lon


def _geometries(obj) -> Iterator[dict]:
    """Yield every atomic geometry object contained in a GeoJSON object."""
    if obj is None:
        return
    if isinstance(obj, list):
        for item in obj:
            yield from _geometries(item)
        return
    if not isinstance(obj, dict):
        return
    t = obj.get("type")
    if t == "FeatureCollection":
        yield from _geometries(obj.get("features") or [])
    elif t == "Feature":
        yield from _geometries(obj.get("geometry"))
    elif t == "GeometryCollection":
        yield from _geometries(obj.get("geometries") or [])
    elif t in ("Point", "MultiPoint") or t in _LINE_TYPES:
        yield obj


def _positions(coords) -> Iterator[Coord]:
    """Flatten a nested coordinate array into individual positions."""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        yield coords
    else:
        for c in coords:
            yield from _positions(c)


def _lines(t: str, coords) -> Iterator[List[Coord]]:
    """Yield each vertex sequence (line or ring) of a line-like geometry."""
    if not coords:
        return
    if t == "LineString":
        yield list(coords)
    elif t in ("MultiLineString", "Polygon"):
        for part in coords:
            yield list(part)
    elif t == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                yield list(ring)


def _arcs_from_line(line: Sequence[Coord]) -> Iterator[Tuple[float, float]]:
    """Longitude arcs covered by a vertex sequence, as unnormalised [a, b]
    intervals of width <= 180 (shortest way around between vertices)."""
    prev = None
    for pos in line:
        lon = _norm_lon(pos[0])
        if prev is not None:
            d = lon - prev
            if d > 180.0:
                d -= 360.0
            elif d < -180.0:
                d += 360.0
            a, b = (prev, prev + d) if d >= 0 else (prev + d, prev)
            yield (a, b)
        prev = lon
    if prev is not None and len(line) == 1:
        yield (prev, prev)


def _split_to_range(a: float, b: float) -> Iterator[Tuple[float, float]]:
    """Split an unnormalised arc into pieces lying inside [-180, 180]."""
    if a < -180.0:
        yield (a + 360.0, 180.0)
        yield (-180.0, b)
    elif b > 180.0:
        yield (a, 180.0)
        yield (-180.0, b - 360.0)
    else:
        yield (a, b)


def _lon_extent(arcs: Iterable[Tuple[float, float]]) -> Tuple[float, float]:
    """Smallest circular longitude interval covering all arcs."""
    pieces: List[Tuple[float, float]] = []
    for a, b in arcs:
        for p in _split_to_range(a, b):
            pieces.append(p)
    if not pieces:
        raise ValueError("no coordinates found")
    pieces.sort()

    merged: List[List[float]] = []
    for a, b in pieces:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])

    # Find the largest uncovered gap on the circle; the box is its complement.
    best_gap = -1.0
    best_idx = -1  # gap between merged[i] and merged[i+1]; -1 means the wrap gap
    for i in range(len(merged) - 1):
        gap = merged[i + 1][0] - merged[i][1]
        if gap > best_gap:
            best_gap, best_idx = gap, i
    wrap_gap = (merged[0][0] + 360.0) - merged[-1][1]
    if wrap_gap >= best_gap:
        best_gap, best_idx = wrap_gap, -1

    if best_gap <= 0.0:
        return -180.0, 180.0
    if best_idx == -1:
        return merged[0][0], merged[-1][1]
    west = merged[best_idx + 1][0]
    east = merged[best_idx][1]
    return _norm_lon(west), _norm_lon(east)


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Coordinates are assumed to be EPSG:4326 longitude/latitude.  Longitudes
    outside ``[-180, 180]`` in the input are wrapped.  Geometry that crosses
    the antimeridian yields a box with ``min_lon > max_lon`` (RFC 7946).
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    min_lat = math.inf
    max_lat = -math.inf
    arcs: List[Tuple[float, float]] = []

    for geom in _geometries(data):
        t = geom["type"]
        coords = geom.get("coordinates")
        if not coords:
            continue
        for pos in _positions(coords):
            lat = float(pos[1])
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat
        if t in ("Point", "MultiPoint"):
            for pos in _positions(coords):
                lon = _norm_lon(pos[0])
                arcs.append((lon, lon))
        else:
            for line in _lines(t, coords):
                arcs.extend(_arcs_from_line(line))

    if not arcs or not math.isfinite(min_lat):
        raise ValueError("GeoJSON contains no coordinates")

    min_lon, max_lon = _lon_extent(arcs)
    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```