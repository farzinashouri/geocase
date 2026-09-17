"""Bounding box of a GeoJSON file in EPSG:4326 (WGS84).

The module exposes a single function, :func:`geojson_bounds`, which returns
``(min_lon, min_lat, max_lon, max_lat)`` for every geometry found in the file.

Longitude handling follows RFC 7946 section 5.2: the returned box is the
smallest arc of longitude that covers the geometry on the sphere, so a
geometry that straddles the antimeridian yields ``min_lon > max_lon``
(for example ``(177.0, -20.0, -178.0, 21.0)``).  Input longitudes outside
``[-180, 180]`` are wrapped before use; output longitudes always lie within
``[-180, 180]``.
"""

from __future__ import annotations

import json
from typing import Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

Position = Sequence[float]
Interval = Tuple[float, float]  # (start, end) with start in [-180, 180), end >= start


def _wrap_lon(lon: float) -> float:
    """Wrap a longitude into the half-open range [-180, 180)."""
    return ((float(lon) + 180.0) % 360.0) - 180.0


def _iter_geometries(obj) -> Iterator[dict]:
    """Yield every concrete geometry object reachable from a GeoJSON object."""
    if not isinstance(obj, dict):
        return
    gtype = obj.get("type")
    if gtype == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _iter_geometries(feature)
    elif gtype == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif gtype == "GeometryCollection":
        for geom in obj.get("geometries") or []:
            yield from _iter_geometries(geom)
    elif gtype in (
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    ):
        yield obj


def _iter_sequences(geom: dict) -> Iterator[Tuple[List[Position], bool]]:
    """Yield ``(positions, connected)`` for a geometry.

    ``connected`` is True when consecutive positions form segments (lines and
    rings) and False when they are independent points.
    """
    coords = geom.get("coordinates")
    if coords is None:
        return
    gtype = geom["type"]
    if gtype == "Point":
        yield [coords], False
    elif gtype == "MultiPoint":
        yield list(coords), False
    elif gtype == "LineString":
        yield list(coords), True
    elif gtype in ("MultiLineString", "Polygon"):
        for part in coords:
            yield list(part), True
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield list(ring), True


def _segment_interval(lon_a: float, lon_b: float) -> Interval:
    """Shortest eastward longitude interval joining two wrapped longitudes."""
    delta = lon_b - lon_a
    if delta > 180.0:
        delta -= 360.0
    elif delta < -180.0:
        delta += 360.0
    start = lon_a if delta >= 0 else lon_a + delta
    start = _wrap_lon(start)
    return start, start + abs(delta)


def _covering_arc(intervals: List[Interval]) -> Tuple[float, float]:
    """Smallest eastward arc ``(start, length)`` covering all intervals."""
    intervals.sort()
    merged: List[List[float]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Merge the last interval into the first one if they touch across the
    # antimeridian.
    if len(merged) > 1 and merged[-1][1] - 360.0 >= merged[0][0]:
        last = merged.pop()
        merged[0][0] = last[0] - 360.0
        merged[0][1] = max(merged[0][1], last[1] - 360.0)

    if len(merged) == 1:
        start, end = merged[0]
        return start, min(end - start, 360.0)

    # Find the largest gap between consecutive merged intervals (including the
    # wrap-around gap); the covering arc is the complement of that gap.
    n = len(merged)
    best_gap = -1.0
    best_idx = 0
    for i in range(n):
        this_end = merged[i][1]
        if i + 1 < n:
            next_start = merged[i + 1][0]
        else:
            next_start = merged[0][0] + 360.0
        gap = next_start - this_end
        if gap > best_gap:
            best_gap = gap
            best_idx = i

    if best_idx == n - 1:
        start = merged[0][0]
        length = merged[-1][1] - start
    else:
        start = merged[best_idx + 1][0]
        length = merged[best_idx][1] + 360.0 - start
    return start, min(length, 360.0)


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Coordinates are assumed to be longitude/latitude in EPSG:4326.  The box is
    the smallest one that covers the geometry on the Earth's surface; when the
    geometry crosses the antimeridian the result has ``min_lon > max_lon`` as
    described in RFC 7946.  Raises ``ValueError`` if the file contains no
    coordinates.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    intervals: List[Interval] = []
    min_lat = float("inf")
    max_lat = float("-inf")

    for geom in _iter_geometries(data):
        for positions, connected in _iter_sequences(geom):
            lons: List[float] = []
            for pos in positions:
                if pos is None or len(pos) < 2:
                    continue
                lon = _wrap_lon(pos[0])
                lat = float(pos[1])
                lons.append(lon)
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
            if not lons:
                continue
            if connected and len(lons) > 1:
                for a, b in zip(lons, lons[1:]):
                    intervals.append(_segment_interval(a, b))
            else:
                for lon in lons:
                    intervals.append((lon, lon))

    if not intervals:
        raise ValueError("GeoJSON contains no coordinates")

    start, length = _covering_arc(intervals)
    if length >= 360.0:
        return -180.0, min_lat, 180.0, max_lat

    min_lon = _wrap_lon(start)
    max_lon = min_lon + length
    if max_lon > 180.0:
        max_lon -= 360.0
    return float(min_lon), float(min_lat), float(max_lon), float(max_lat)