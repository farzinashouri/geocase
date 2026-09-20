```python
"""Bounding boxes for GeoJSON files in EPSG:4326 (WGS84).

The only interesting part of this problem is longitude.  Latitude is a plain
linear axis, so ``min``/``max`` over the vertices is correct.  Longitude is
*cyclic*: taking ``min``/``max`` over raw coordinates gives a bogus, nearly
global box for anything that straddles the antimeridian (e.g. Fiji, the
Chukchi Sea, a flight path Tokyo -> Los Angeles).

This module therefore:

1. Walks each connected vertex path (ring / linestring) and *unwraps* longitude
   so that a step of more than 180 degrees is read as an antimeridian crossing
   rather than a jump right across the planet.
2. Detects rings that encircle a pole (their unwrapped longitude winds a full
   360 degrees) and gives them the full longitude range.
3. Merges every part's longitude arc on the circle and returns the *smallest*
   arc that covers them all, found as the complement of the largest empty gap.

The returned longitudes always lie in ``[-180, 180]``.  When the tightest box
crosses the antimeridian, ``min_lon > max_lon``; that is the RFC 7946
convention for such boxes and it is the only way to describe the real extent
without inflating it to the whole globe.

No side effects on import.
"""

from __future__ import annotations

import json
from typing import Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

_EPS = 1e-9


# --------------------------------------------------------------------------
# GeoJSON traversal
# --------------------------------------------------------------------------

def _geometries(obj) -> Iterator[dict]:
    """Yield every geometry dict in a GeoJSON object (any top-level type)."""
    if not isinstance(obj, dict):
        return
    kind = obj.get("type")
    if kind == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _geometries(feature)
    elif kind == "Feature":
        yield from _geometries(obj.get("geometry"))
    elif kind == "GeometryCollection":
        for geom in obj.get("geometries") or []:
            yield from _geometries(geom)
    elif kind in (
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    ):
        if obj.get("coordinates"):
            yield obj


def _paths(geom: dict) -> Iterator[Tuple[List[Tuple[float, float]], bool]]:
    """Yield ``(vertices, closed)`` for each connected part of a geometry.

    Isolated points are yielded as single-vertex paths: there is no edge
    information to infer a crossing from, so each one is simply its own point
    on the longitude circle.
    """
    kind = geom["type"]
    coords = geom["coordinates"]

    def pts(seq: Sequence) -> List[Tuple[float, float]]:
        return [(float(c[0]), float(c[1])) for c in seq if c is not None and len(c) >= 2]

    if kind == "Point":
        yield pts([coords]), False
    elif kind == "MultiPoint":
        for c in coords:
            yield pts([c]), False
    elif kind == "LineString":
        yield pts(coords), False
    elif kind == "MultiLineString":
        for line in coords:
            yield pts(line), False
    elif kind == "Polygon":
        for ring in coords:
            yield pts(ring), True
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield pts(ring), True


# --------------------------------------------------------------------------
# Longitude helpers
# --------------------------------------------------------------------------

def _wrap180(lon: float) -> float:
    """Normalise a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _unwrap(lons: Sequence[float]) -> List[float]:
    """Make a longitude sequence continuous by removing 360-degree jumps."""
    out = [lons[0]]
    for lon in lons[1:]:
        step = (lon - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + step)
    return out


def _merge(segments: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Merge overlapping/touching closed segments given in [-180, 180]."""
    segments.sort()
    merged: List[Tuple[float, float]] = []
    for start, end in segments:
        if merged and start <= merged[-1][1] + _EPS:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def _covering_arc(arcs: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Smallest arc on the longitude circle covering every ``(start, width)``.

    Found as the complement of the largest gap left uncovered by the union of
    the input arcs.
    """
    segments: List[Tuple[float, float]] = []
    for start, width in arcs:
        if width >= 360.0 - _EPS:
            return (-180.0, 180.0)
        start = _wrap180(start)
        end = start + width
        if end <= 180.0:
            segments.append((start, end))
        else:  # crosses the antimeridian: split at +/-180
            segments.append((start, 180.0))
            segments.append((-180.0, end - 360.0))

    merged = _merge(segments)
    # The segment list lives on a circle, so the piece from the last segment's
    # end round to the first segment's start is a gap too.
    best_gap = -1.0
    best: Tuple[float, float] = (-180.0, 180.0)
    count = len(merged)
    for i, (_, gap_start) in enumerate(merged):
        nxt = merged[(i + 1) % count][0]
        gap_end = nxt + (360.0 if i == count - 1 else 0.0)
        gap = gap_end - gap_start
        if gap > best_gap:
            best_gap = gap
            best = (gap_end, gap_start)  # box runs eastward from gap end to gap start

    if best_gap <= _EPS:
        return (-180.0, 180.0)
    min_lon, max_lon = best
    return (_wrap180(min_lon), _wrap180(max_lon))


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Coordinates are assumed to be EPSG:4326 longitude/latitude.  Output
    longitudes are in ``[-180, 180]``; for an extent that crosses the
    antimeridian ``min_lon > max_lon``, meaning the box runs eastward from
    ``min_lon``, over +/-180, to ``max_lon``.

    Raises ``ValueError`` if the file contains no usable coordinates.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    arcs: List[Tuple[float, float]] = []       # (start_lon, width)
    lats: List[float] = []
    poles: List[float] = []                    # sign of any encircled pole

    for geom in _geometries(data):
        for vertices, closed in _paths(geom):
            if not vertices:
                continue
            lons = _unwrap([v[0] for v in vertices])
            part_lats = [v[1] for v in vertices]
            lats.extend(part_lats)

            winding = lons[-1] - lons[0]
            if closed and abs(winding) > 180.0:
                # The ring winds all the way around: it encloses a pole, so
                # every longitude is inside it.
                arcs.append((-180.0, 360.0))
                poles.append(1.0 if sum(part_lats) >= 0 else -1.0)
                continue

            low, high = min(lons), max(lons)
            width = min(high - low, 360.0)
            arcs.append((low, width))

    if not arcs or not lats:
        raise ValueError(f"no coordinates found in {path!r}")

    min_lon, max_lon = _covering_arc(arcs)
    min_lat, max_lat = min(lats), max(lats)
    for sign in poles:
        if sign > 0:
            max_lat = 90.0
        else:
            min_lat = -90.0

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```