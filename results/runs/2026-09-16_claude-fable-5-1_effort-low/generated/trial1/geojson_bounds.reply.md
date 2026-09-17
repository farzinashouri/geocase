```python
"""Compute the geographic bounding box of a GeoJSON file.

The bounding box follows the GeoJSON (RFC 7946) convention: when the data
crosses the antimeridian, ``min_lon`` is greater than ``max_lon`` so the box
describes the real extent on Earth instead of wrapping around the globe.
All longitudes in the result are within ``[-180, 180]``.
"""

import json
import math
from typing import Iterable, Iterator, List, Sequence, Tuple

BBox = Tuple[float, float, float, float]


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def _iter_parts(geometry) -> Iterator[Sequence[Sequence[float]]]:
    """Yield each connected coordinate sequence (point, line, ring) of a geometry."""
    if geometry is None:
        return
    gtype = geometry.get("type")
    if gtype == "GeometryCollection":
        for geom in geometry.get("geometries") or []:
            yield from _iter_parts(geom)
        return
    coords = geometry.get("coordinates")
    if coords is None:
        return
    if gtype == "Point":
        yield [coords]
    elif gtype in ("MultiPoint", "LineString"):
        if gtype == "MultiPoint":
            for c in coords:
                yield [c]
        else:
            yield coords
    elif gtype in ("MultiLineString", "Polygon"):
        for part in coords:
            yield part
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                yield ring
    else:
        raise ValueError(f"Unsupported geometry type: {gtype!r}")


def _iter_geometries(obj) -> Iterator[dict]:
    """Yield every geometry object contained in a GeoJSON object."""
    if obj is None:
        return
    otype = obj.get("type")
    if otype == "FeatureCollection":
        for feat in obj.get("features") or []:
            yield from _iter_geometries(feat)
    elif otype == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    else:
        yield obj


def _unwrapped_lon_interval(part: Sequence[Sequence[float]]) -> Tuple[float, float]:
    """Return (start, end) longitude interval of a connected part.

    Consecutive vertices are assumed to take the short way around, so jumps
    larger than 180 degrees are treated as antimeridian crossings.
    """
    lons = [float(c[0]) for c in part]
    prev = _normalize_lon(lons[0])
    lo = hi = prev
    for lon in lons[1:]:
        cur = _normalize_lon(lon)
        delta = cur - prev
        if delta > 180.0:
            cur -= 360.0 * math.ceil((delta - 180.0) / 360.0)
        elif delta < -180.0:
            cur += 360.0 * math.ceil((-delta - 180.0) / 360.0)
        lo = min(lo, cur)
        hi = max(hi, cur)
        prev = cur
    return lo, hi


def _covering_lon_range(intervals: Iterable[Tuple[float, float]]) -> Tuple[float, float]:
    """Find the smallest arc of the circle covering all longitude intervals."""
    norm: List[Tuple[float, float]] = []
    for lo, hi in intervals:
        if hi - lo >= 360.0:
            return -180.0, 180.0
        start = _normalize_lon(lo)
        norm.append((start, start + (hi - lo)))
    norm.sort()

    merged: List[List[float]] = []
    for start, end in norm:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Merge the last interval into the first if it wraps around to reach it.
    while len(merged) > 1 and merged[-1][1] - 360.0 >= merged[0][0]:
        last = merged.pop()
        merged[0][0] = last[0] - 360.0
        merged[0][1] = max(merged[0][1], last[1] - 360.0)

    if len(merged) == 1:
        start, end = merged[0]
    else:
        # The covering arc is the complement of the largest gap.
        best_gap = -1.0
        best_idx = 0
        for i in range(len(merged)):
            nxt = merged[(i + 1) % len(merged)]
            gap_start = merged[i][1]
            gap_end = nxt[0] + (360.0 if i == len(merged) - 1 else 0.0)
            gap = gap_end - gap_start
            if gap > best_gap:
                best_gap, best_idx = gap, i
        start = merged[(best_idx + 1) % len(merged)][0]
        end = merged[best_idx][1]
        if end < start:
            end += 360.0

    if end - start >= 360.0:
        return -180.0, 180.0
    min_lon = _normalize_lon(start)
    max_lon = _normalize_lon(end)
    if max_lon == -180.0 and end - start > 0.0:
        max_lon = 180.0
    return min_lon, max_lon


def geojson_bounds(path) -> BBox:
    """Return (min_lon, min_lat, max_lon, max_lat) for a WGS84 GeoJSON file.

    If the geometry crosses the antimeridian, ``min_lon > max_lon`` as in
    RFC 7946 so that the box covers the actual extent of the data.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    lon_intervals: List[Tuple[float, float]] = []
    min_lat = math.inf
    max_lat = -math.inf

    for geometry in _iter_geometries(data):
        for part in _iter_parts(geometry):
            if not part:
                continue
            lon_intervals.append(_unwrapped_lon_interval(part))
            for c in part:
                lat = float(c[1])
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat

    if not lon_intervals:
        raise ValueError("GeoJSON contains no coordinates")

    min_lon, max_lon = _covering_lon_range(lon_intervals)
    min_lat = max(-90.0, min(90.0, min_lat))
    max_lat = max(-90.0, min(90.0, max_lat))
    return float(min_lon), float(min_lat), float(max_lon), float(max_lat)


__all__ = ["geojson_bounds"]
```