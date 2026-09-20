"""Bounding box of a GeoJSON file in EPSG:4326 (lon/lat degrees).

The returned box describes the true extent of the geometry on Earth: for
data that crosses the antimeridian the box is the *short* way around, in
which case ``min_lon > max_lon``. All longitudes are in [-180, 180].
"""

from __future__ import annotations

import json
from typing import Any, Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

BBox = Tuple[float, float, float, float]


def geojson_bounds(path) -> BBox:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for every feature in *path*."""
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    lats: List[float] = []
    arcs: List[Tuple[float, float]] = []  # (start_lon, arc_length) pairs

    for part in _coordinate_sequences(doc):
        lons = [float(p[0]) for p in part]
        lats.extend(float(p[1]) for p in part)
        arcs.append(_unwrapped_span(lons))

    if not lats:
        raise ValueError("no coordinates found in GeoJSON document")

    min_lon, max_lon = _merge_arcs(arcs)
    return (min_lon, min(lats), max_lon, max(lats))


def _coordinate_sequences(node: Any) -> Iterator[Sequence[Sequence[float]]]:
    """Yield each connected run of positions (ring, linestring or lone point)."""
    if isinstance(node, list):
        for item in node:
            yield from _coordinate_sequences(item)
        return
    if not isinstance(node, dict):
        return

    kind = node.get("type")
    if kind == "FeatureCollection":
        yield from _coordinate_sequences(node.get("features") or [])
    elif kind == "Feature":
        geom = node.get("geometry")
        if geom is not None:
            yield from _coordinate_sequences(geom)
    elif kind == "GeometryCollection":
        yield from _coordinate_sequences(node.get("geometries") or [])
    elif kind in ("Point", "MultiPoint", "LineString", "MultiLineString",
                  "Polygon", "MultiPolygon"):
        coords = node.get("coordinates")
        if coords is None:
            return
        depth = {"Point": 0, "MultiPoint": 1, "LineString": 1,
                 "MultiLineString": 2, "Polygon": 2, "MultiPolygon": 3}[kind]
        if depth == 0:
            yield [coords]
        elif kind == "MultiPoint":
            # Points are not connected to one another; keep them independent.
            for position in coords:
                yield [position]
        else:
            yield from _runs(coords, depth)


def _runs(coords: Any, depth: int) -> Iterator[Sequence[Sequence[float]]]:
    if depth == 1:
        yield coords
        return
    for sub in coords:
        yield from _runs(sub, depth - 1)


def _unwrapped_span(lons: Sequence[float]) -> Tuple[float, float]:
    """Span of one connected run, following each segment the short way around.

    Returns ``(start, length)`` where ``length`` is in [0, 360].
    """
    current = _normalize(lons[0])
    lo = hi = current
    for raw in lons[1:]:
        step = _normalize(_normalize(raw) - current)
        if step == -180.0:
            step = 180.0  # exactly antipodal: direction is arbitrary
        current += step
        lo = min(lo, current)
        hi = max(hi, current)
    length = hi - lo
    return (_normalize(lo), 360.0 if length >= 360.0 else length)


def _merge_arcs(arcs: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Union arcs on the longitude circle, then return the tightest box."""
    segments: List[List[float]] = []
    for start, length in arcs:
        if length >= 360.0:
            return (-180.0, 180.0)
        end = start + length
        if end > 180.0:
            segments.append([start, 180.0])
            segments.append([-180.0, end - 360.0])
        else:
            segments.append([start, end])

    segments.sort()
    merged: List[List[float]] = [segments[0]]
    for start, end in segments[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    if len(merged) == 1:
        return (merged[0][0], merged[0][1])

    # Largest uncovered gap; the bounding box is its complement.
    gap = -1.0
    after = 0
    for i in range(len(merged)):
        j = (i + 1) % len(merged)
        width = merged[j][0] - merged[i][1]
        if j == 0:
            width += 360.0
        if width > gap:
            gap, after = width, j
    if gap <= 0.0:
        return (-180.0, 180.0)

    before = (after - 1) % len(merged)
    return (_normalize(merged[after][0]), _normalize(merged[before][1]))


def _normalize(lon: float) -> float:
    """Wrap a longitude into [-180, 180]."""
    lon = float(lon)
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = (lon + 180.0) % 360.0 - 180.0
    return wrapped