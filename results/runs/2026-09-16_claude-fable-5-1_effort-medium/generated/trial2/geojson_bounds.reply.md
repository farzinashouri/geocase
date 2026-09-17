```python
"""Compute the geographic bounding box of a GeoJSON file.

The bounding box is reported as ``(min_lon, min_lat, max_lon, max_lat)``.
Coordinates are assumed to be longitude/latitude in EPSG:4326.  Geometries
that cross the antimeridian are handled by treating longitude as a circle:
the reported box is the smallest longitudinal arc that covers every segment
of the geometry, and following RFC 7946 section 5.2, a box that crosses the
antimeridian has ``min_lon > max_lon``.  All returned longitudes lie in
``[-180, 180]``.
"""

import json
from typing import Iterable, Iterator, List, Sequence, Tuple

Coord = Sequence[float]
Segment = Tuple[float, float]  # (start_lon, end_lon), non-wrapping on [-180, 180]


def _norm_lon(lon: float) -> float:
    """Normalise a longitude into [-180, 180]."""
    lon = float(lon)
    if -180.0 <= lon <= 180.0:
        return lon
    lon = ((lon + 180.0) % 360.0) - 180.0
    return lon


def _iter_geometries(obj) -> Iterator[dict]:
    """Yield every non-collection geometry object reachable from a GeoJSON object."""
    if obj is None:
        return
    if isinstance(obj, list):
        for item in obj:
            yield from _iter_geometries(item)
        return
    if not isinstance(obj, dict):
        return
    kind = obj.get("type")
    if kind == "FeatureCollection":
        yield from _iter_geometries(obj.get("features") or [])
    elif kind == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif kind == "GeometryCollection":
        yield from _iter_geometries(obj.get("geometries") or [])
    elif kind in ("Point", "MultiPoint", "LineString", "MultiLineString",
                  "Polygon", "MultiPolygon"):
        yield obj


def _iter_paths(geom: dict) -> Iterator[List[Coord]]:
    """Yield coordinate sequences: each is a connected path (points as length-1)."""
    kind = geom["type"]
    coords = geom.get("coordinates")
    if coords is None:
        return
    if kind == "Point":
        yield [coords]
    elif kind == "MultiPoint":
        for c in coords:
            yield [c]
    elif kind == "LineString":
        yield coords
    elif kind in ("MultiLineString", "Polygon"):
        for part in coords:
            yield part
    elif kind == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                yield ring


def _path_segments(path: Iterable[Coord]) -> Iterator[Segment]:
    """Turn a connected coordinate path into non-wrapping longitude intervals."""
    prev = None
    for c in path:
        lon = _norm_lon(c[0])
        if prev is None:
            yield (lon, lon)
        else:
            a, b = prev, lon
            if abs(b - a) > 180.0:
                # Shortest path crosses the antimeridian: split at +/-180.
                lo, hi = (a, b) if a > b else (b, a)
                yield (lo, 180.0)
                yield (-180.0, hi)
            else:
                yield (min(a, b), max(a, b))
        prev = lon


def _merge(segments: List[Segment]) -> List[Segment]:
    segments.sort()
    merged: List[Segment] = []
    for s, e in segments:
        if merged and s <= merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def _lon_extent(segments: List[Segment]) -> Tuple[float, float]:
    """Smallest arc on the longitude circle covering all segments."""
    merged = _merge(segments)
    if len(merged) == 1:
        return merged[0]
    # Gaps between consecutive merged intervals, plus the gap across +/-180.
    best_gap = (merged[0][0] + 360.0) - merged[-1][1]
    best_idx = None  # None means the wrap gap is the largest
    for i in range(len(merged) - 1):
        gap = merged[i + 1][0] - merged[i][1]
        if gap > best_gap:
            best_gap = gap
            best_idx = i
    if best_idx is None:
        return merged[0][0], merged[-1][1]
    # The largest gap is interior: the box wraps across the antimeridian.
    west = merged[best_idx + 1][0]
    east = merged[best_idx][1]
    return west, east


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Longitudes are always within ``[-180, 180]``.  If the geometry crosses
    the antimeridian the box wraps and ``min_lon > max_lon`` (RFC 7946).

    Raises ``ValueError`` if the file contains no coordinates.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    segments: List[Segment] = []
    min_lat = float("inf")
    max_lat = float("-inf")

    for geom in _iter_geometries(data):
        for coord_path in _iter_paths(geom):
            for c in coord_path:
                lat = float(c[1])
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
            segments.extend(_path_segments(coord_path))

    if not segments:
        raise ValueError("GeoJSON contains no coordinates: %r" % (path,))

    min_lon, max_lon = _lon_extent(segments)
    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```