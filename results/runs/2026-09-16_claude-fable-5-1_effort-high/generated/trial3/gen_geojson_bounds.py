"""Compute the WGS84 bounding box of a GeoJSON file.

The result is ``(min_lon, min_lat, max_lon, max_lat)``. Longitudes are always
within ``[-180, 180]``. When the data straddles the antimeridian, the box is
reported the RFC 7946 way: ``min_lon`` (west edge) is greater than ``max_lon``
(east edge), e.g. ``(170.0, 10.0, -170.0, 20.0)``, rather than a box that
wrongly spans almost the whole globe.
"""

import json
from typing import Any, Iterator, List, Optional, Sequence, Tuple

Coord = Tuple[float, float]
Interval = Tuple[float, float]
BBox = Tuple[float, float, float, float]

__all__ = ["geojson_bounds"]


def _norm_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180], leaving in-range values untouched."""
    lon = float(lon)
    if -180.0 <= lon <= 180.0:
        return lon
    return (lon + 180.0) % 360.0 - 180.0


def _point(position: Sequence[Any]) -> Coord:
    if len(position) < 2:
        raise ValueError("GeoJSON position needs at least two ordinates")
    return _norm_lon(position[0]), float(position[1])


def _paths(obj: Optional[dict]) -> Iterator[List[Coord]]:
    """Yield connected vertex sequences (points are length-1 paths)."""
    if obj is None:
        return
    gtype = obj.get("type")
    if gtype == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _paths(feature)
    elif gtype == "Feature":
        yield from _paths(obj.get("geometry"))
    elif gtype == "GeometryCollection":
        for geom in obj.get("geometries") or []:
            yield from _paths(geom)
    elif gtype in ("Point", "MultiPoint", "LineString", "MultiLineString",
                   "Polygon", "MultiPolygon"):
        coords = obj.get("coordinates")
        if coords is None:
            return
        if gtype == "Point":
            yield [_point(coords)]
        elif gtype == "MultiPoint":
            for c in coords:
                yield [_point(c)]
        elif gtype == "LineString":
            yield [_point(c) for c in coords]
        elif gtype in ("MultiLineString", "Polygon"):
            for line in coords:
                yield [_point(c) for c in line]
        else:  # MultiPolygon
            for polygon in coords:
                for ring in polygon:
                    yield [_point(c) for c in ring]
    else:
        raise ValueError(f"Unsupported GeoJSON type: {gtype!r}")


def _segment_intervals(lon_a: float, lon_b: float) -> List[Interval]:
    """Linear sub-intervals of [-180, 180] covered by the shorter arc a->b."""
    lo, hi = (lon_a, lon_b) if lon_a <= lon_b else (lon_b, lon_a)
    span = hi - lo
    if span <= 180.0:          # ordinary segment (ties resolve to non-crossing)
        return [(lo, hi)]
    if span >= 360.0:          # -180 <-> 180: same meridian, treat as full width
        return [(-180.0, 180.0)]
    return [(hi, 180.0), (-180.0, lo)]   # crosses the antimeridian


def _merge(intervals: List[Interval]) -> List[Interval]:
    intervals.sort()
    merged: List[List[float]] = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1]:
            if hi > merged[-1][1]:
                merged[-1][1] = hi
        else:
            merged.append([lo, hi])
    return [(lo, hi) for lo, hi in merged]


def _lon_extent(intervals: List[Interval]) -> Tuple[float, float]:
    """Smallest longitude arc covering all intervals, as (west, east)."""
    merged = _merge(intervals)
    west, east = merged[0][0], merged[-1][1]
    best_gap = (180.0 - east) + (west + 180.0)   # gap that wraps through ±180
    for (_, prev_hi), (next_lo, _) in zip(merged, merged[1:]):
        gap = next_lo - prev_hi
        if gap > best_gap:                       # strict: prefer non-crossing on ties
            best_gap = gap
            west, east = next_lo, prev_hi        # crossing box: west > east
    return west, east


def geojson_bounds(path: str) -> BBox:
    """Return (min_lon, min_lat, max_lon, max_lat) for a GeoJSON file.

    Coordinates are assumed to be EPSG:4326 longitude/latitude. Geometry that
    straddles the antimeridian yields min_lon > max_lon (RFC 7946 style).
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    intervals: List[Interval] = []
    min_lat = float("inf")
    max_lat = float("-inf")

    for path_coords in _paths(data):
        if not path_coords:
            continue
        for lon, lat in path_coords:
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat
        if len(path_coords) == 1:
            lon = path_coords[0][0]
            intervals.append((lon, lon))
        else:
            for (lon_a, _), (lon_b, _) in zip(path_coords, path_coords[1:]):
                intervals.extend(_segment_intervals(lon_a, lon_b))

    if not intervals:
        raise ValueError(f"No coordinates found in {path!r}")

    west, east = _lon_extent(intervals)
    return float(west), float(min_lat), float(east), float(max_lat)