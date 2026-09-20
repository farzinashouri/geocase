"""Bounding box of a GeoJSON file in EPSG:4326 (WGS84).

``geojson_bounds(path)`` returns ``(min_lon, min_lat, max_lon, max_lat)`` for
every geometry in the file. Longitudes are normalised into ``[-180, 180]``.

Longitude is circular, so the box is computed as the smallest arc of the
globe that covers every point and every edge of the input (edges are taken
along the shorter great-circle direction, the usual GeoJSON convention).
When that arc crosses the antimeridian the result follows RFC 7946 §5.2:
``min_lon`` is greater than ``max_lon`` (for example ``(170.0, -10.0,
-170.0, 10.0)``). Geometry covering every longitude yields ``-180`` / ``180``.
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterator, List, Tuple

__all__ = ["geojson_bounds"]

_NUMBER = (int, float)
_LINEAR_TYPES = {"LineString", "MultiLineString", "Polygon", "MultiPolygon"}


def _wrap_lon(lon: float) -> float:
    """Map any longitude onto [-180, 180], keeping +180 as +180."""
    if -180.0 <= lon <= 180.0:
        return float(lon)
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0:
        wrapped += 360.0
    return wrapped - 180.0


def _iter_geometries(obj: Any) -> Iterator[dict]:
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
    elif gtype is not None and "coordinates" in obj:
        yield obj


def _is_position(node: Any) -> bool:
    return (
        isinstance(node, (list, tuple))
        and len(node) >= 2
        and isinstance(node[0], _NUMBER)
        and isinstance(node[1], _NUMBER)
    )


def _walk(node: Any, linear: bool, points: list, edges: list) -> None:
    """Collect positions and, for linear geometries, consecutive-vertex edges."""
    if not isinstance(node, (list, tuple)) or not node:
        return
    if _is_position(node):
        points.append((float(node[0]), float(node[1])))
        return
    if all(_is_position(child) for child in node):
        coords = [(float(c[0]), float(c[1])) for c in node]
        points.extend(coords)
        if linear:
            edges.extend(zip(coords[:-1], coords[1:]))
        return
    for child in node:
        _walk(child, linear, points, edges)


def _lon_extent(points: List[Tuple[float, float]],
                edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]
                ) -> Tuple[float, float]:
    """Smallest longitude arc covering all points and edges.

    Returns ``(start, end)``; ``start > end`` means the arc crosses the
    antimeridian.
    """
    arcs: List[Tuple[float, float]] = []
    for lon, _ in points:
        s = _wrap_lon(lon)
        arcs.append((s, s))
    for (a_lon, _), (b_lon, _) in edges:
        a = _wrap_lon(a_lon)
        b = _wrap_lon(b_lon)
        delta = math.fmod(b - a + 540.0, 360.0) - 180.0  # shorter direction, (-180, 180]
        if delta < 0:
            a, delta = b, -delta
        arcs.append((a, a + delta))

    # Unroll onto two periods so wrap-around gaps are seen once linearly.
    unrolled = []
    for s, e in arcs:
        if s == 180.0:
            s, e = -180.0, e - 360.0
        unrolled.append((s, e))
        unrolled.append((s + 360.0, e + 360.0))
    unrolled.sort()

    merged: List[List[float]] = []
    for s, e in unrolled:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    best_gap = -1.0
    best_start = best_end = None
    for cur, nxt in zip(merged, merged[1:]):
        gap = nxt[0] - cur[1]
        if gap > best_gap:
            best_gap = gap
            best_start, best_end = nxt[0], cur[1]

    if best_start is None or best_gap <= 0.0:
        return -180.0, 180.0  # coverage wraps the whole globe

    start = _wrap_lon(best_start)
    end = _wrap_lon(best_end)
    if start == 180.0:
        start = -180.0
    if end == -180.0 and start != -180.0:
        end = 180.0
    return start, end


def geojson_bounds(path: str) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` of a GeoJSON file.

    Coordinates must be WGS84 longitude/latitude. Output longitudes lie in
    ``[-180, 180]``; a box that crosses the antimeridian has
    ``min_lon > max_lon`` as prescribed by RFC 7946.

    Raises ``ValueError`` if the file contains no coordinates.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    points: List[Tuple[float, float]] = []
    edges: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for geom in _iter_geometries(data):
        linear = geom.get("type") in _LINEAR_TYPES
        _walk(geom.get("coordinates"), linear, points, edges)

    if not points:
        raise ValueError(f"no coordinates found in {path!r}")

    lats = [lat for _, lat in points]
    min_lon, max_lon = _lon_extent(points, edges)
    return (float(min_lon), float(min(lats)), float(max_lon), float(max(lats)))