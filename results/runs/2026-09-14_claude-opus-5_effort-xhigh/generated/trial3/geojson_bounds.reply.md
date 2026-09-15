Note on the one design decision worth flagging: longitudes are treated as a circle, so a feature straddling the antimeridian gets its true narrow extent, which per RFC 7946 §5.2 is reported with `min_lon > max_lon` (both still within `[-180, 180]`).

```python
"""Bounding box of a GeoJSON file in EPSG:4326 (WGS84).

The returned box describes the true extent of the geometry on the globe, so a
feature that straddles the antimeridian yields the short box across 180deg
rather than a box that spans the whole planet.  Following RFC 7946 section
5.2, such a box is reported with ``min_lon > max_lon``; both longitudes always
stay inside ``[-180, 180]``.
"""

from __future__ import annotations

import json
import math
from typing import Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

Position = Sequence[float]
Bounds = Tuple[float, float, float, float]

_GEOMETRY_TYPES = frozenset(
    {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    }
)


def geojson_bounds(path) -> Bounds:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` points at a GeoJSON document holding a FeatureCollection, a
    Feature or a bare geometry, with longitude/latitude coordinates in
    EPSG:4326.  Any ``bbox`` member in the document is ignored; the extent is
    computed from the coordinates themselves.

    Longitudes are treated as points on a circle, so the result is the
    narrowest longitude band containing every coordinate.  If that band crosses
    the antimeridian the returned ``min_lon`` is greater than ``max_lon``
    (RFC 7946 section 5.2), e.g. ``(178.0, -18.0, -178.0, -16.0)`` for a small
    feature near Fiji.

    Raises ``ValueError`` if the document is not usable GeoJSON or holds no
    coordinates.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    latitudes: List[float] = []
    spans: List[Tuple[float, float]] = []

    for geometry in _iter_geometries(document):
        for run in _iter_runs(geometry):
            longitudes: List[float] = []
            for position in run:
                lon, lat = _position(position)
                longitudes.append(lon)
                latitudes.append(lat)
            if longitudes:
                spans.append(_longitude_span(longitudes))

    if not latitudes:
        raise ValueError(f"GeoJSON document has no coordinates: {path!r}")

    min_lon, max_lon = _longitude_extent(spans)
    return (min_lon, min(latitudes), max_lon, max(latitudes))


def _iter_geometries(node: object) -> Iterator[dict]:
    """Yield every non-null geometry object reachable from ``node``."""
    if not isinstance(node, dict):
        raise ValueError(f"expected a GeoJSON object, got {type(node).__name__}")

    kind = node.get("type")
    if kind == "FeatureCollection":
        for feature in node.get("features") or []:
            yield from _iter_geometries(feature)
    elif kind == "Feature":
        geometry = node.get("geometry")
        if geometry is not None:  # a null geometry is legal and contributes nothing
            yield from _iter_geometries(geometry)
    elif kind == "GeometryCollection":
        for geometry in node.get("geometries") or []:
            yield from _iter_geometries(geometry)
    elif kind in _GEOMETRY_TYPES:
        yield node
    else:
        raise ValueError(f"unsupported GeoJSON type: {kind!r}")


def _iter_runs(geometry: dict) -> Iterator[Sequence[Position]]:
    """Yield the geometry's positions grouped into connected runs.

    A run is a sequence whose consecutive positions are joined by an edge (a
    line or a polygon ring); isolated points are yielded as one-element runs.
    Keeping the connectivity lets :func:`_longitude_span` tell an edge that
    hops the antimeridian from one that spans the globe the long way.
    """
    kind = geometry["type"]
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return

    if kind == "Point":
        yield [coordinates]
    elif kind == "MultiPoint":
        for point in coordinates:
            yield [point]
    elif kind == "LineString":
        yield coordinates
    elif kind in ("MultiLineString", "Polygon"):
        for line in coordinates:
            if line:
                yield line
    elif kind == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon or []:
                if ring:
                    yield ring
    else:  # pragma: no cover - _iter_geometries filters the type first
        raise ValueError(f"unsupported GeoJSON geometry type: {kind!r}")


def _position(position: Position) -> Tuple[float, float]:
    """Return ``(lon, lat)`` from a GeoJSON position, dropping any elevation."""
    try:
        lon = float(position[0])
        lat = float(position[1])
    except (TypeError, ValueError, IndexError, KeyError) as exc:
        raise ValueError(f"invalid GeoJSON position: {position!r}") from exc
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(f"non-finite GeoJSON position: {position!r}")
    return lon, lat


def _longitude_span(longitudes: Sequence[float]) -> Tuple[float, float]:
    """Return the ``(start, width)`` arc in degrees covered by one run.

    Longitudes are unwrapped so each edge takes the shorter way round: a step
    from 179 to -179 counts as 2 degrees east, not 358 degrees west.  A run
    that keeps going the same way (a ring around a pole) accumulates past a
    full turn and is clamped to the whole circle.
    """
    unwrapped = [_wrap180(longitudes[0])]
    for lon in longitudes[1:]:
        previous = unwrapped[-1]
        step = (lon - previous + 180.0) % 360.0 - 180.0
        unwrapped.append(previous + step)

    low = min(unwrapped)
    width = min(max(unwrapped) - low, 360.0)
    return (low % 360.0, width)


def _longitude_extent(spans: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Return ``(min_lon, max_lon)`` covering every arc in ``spans``.

    The narrowest covering arc is the complement of the widest uncovered gap,
    so the arcs are merged on ``[0, 360)`` and the largest hole is removed.
    """
    segments: List[Tuple[float, float]] = []
    for start, width in spans:
        if width >= 360.0:
            return (-180.0, 180.0)
        end = start + width
        if end > 360.0:  # split the wrap so plain interval merging works
            segments.append((start, 360.0))
            segments.append((0.0, end - 360.0))
        else:
            segments.append((start, end))

    segments.sort()
    merged: List[List[float]] = []
    for start, end in segments:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # The gap that wraps past 0deg, then every gap between merged arcs.
    widest = merged[0][0] + 360.0 - merged[-1][1]
    widest_index = -1
    for index in range(len(merged) - 1):
        gap = merged[index + 1][0] - merged[index][1]
        if gap > widest:
            widest, widest_index = gap, index

    if widest_index == -1:
        low, high = merged[0][0], merged[-1][1]
    else:
        low, high = merged[widest_index + 1][0], merged[widest_index][1] + 360.0

    if high - low >= 360.0:
        return (-180.0, 180.0)
    return (_wrap180(low), _wrap180(high))


def _wrap180(lon: float) -> float:
    """Fold a longitude into ``[-180, 180]``, leaving in-range values alone."""
    if -180.0 <= lon <= 180.0:
        return float(lon)
    wrapped = (lon + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 else wrapped
```