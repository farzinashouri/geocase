Permissions blocked writing/running a scratch file, so I verified the algorithm by hand rather than by execution. Key design point: longitudes are reduced to the *narrowest arc* containing all coordinates, so a dataset straddling the antimeridian reports its real extent, written RFC 7946 §5.2 style with `min_lon > max_lon` (e.g. Fiji → `(177.0, -20.0, -178.0, -16.0)`), with both values inside `[-180, 180]`.

```python
"""Bounding boxes for EPSG:4326 GeoJSON files, aware of the antimeridian."""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, Iterator, List, Sequence, Tuple, Union

__all__ = ["geojson_bounds"]

BBox = Tuple[float, float, float, float]
Position = Sequence[float]
Arc = Tuple[float, float]

_FULL_CIRCLE = 360.0
_HALF_CIRCLE = 180.0

_GEOMETRY_TYPES = frozenset(
    {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }
)


def geojson_bounds(path: Union[str, bytes, "os.PathLike[str]"]) -> BBox:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    The longitudes describe the narrowest east-west span containing every
    coordinate, so data hugging the antimeridian reports its true extent
    rather than the whole planet.  As in RFC 7946 section 5.2, such a box is
    written with ``min_lon > max_lon``: it runs east from ``min_lon``, across
    the antimeridian, to ``max_lon``.  Both stay within [-180, 180].
    """
    with open(path, "r", encoding="utf-8-sig") as handle:
        document = json.load(handle)

    lats: List[float] = []
    arcs: List[Arc] = []
    wraps_world = False

    for geometry in _iter_geometries(document):
        for positions in _iter_paths(geometry):
            lons: List[float] = []
            for position in positions:
                if len(position) < 2:
                    continue
                lons.append(_wrap_lon(float(position[0])))
                lats.append(float(position[1]))
            if not lons:
                continue
            # Every later vertex is an endpoint of one of the segments below.
            arcs.append((lons[0], 0.0))
            for start, end in zip(lons, lons[1:]):
                delta = end - start
                if abs(delta) >= _FULL_CIRCLE:
                    wraps_world = True
                    continue
                if abs(delta) > _HALF_CIRCLE:
                    # RFC 7946 asks for geometries to be cut at the
                    # antimeridian, so a step longer than half the world is
                    # read as the short hop across it.
                    delta -= math.copysign(_FULL_CIRCLE, delta)
                if delta >= 0.0:
                    arcs.append((start, delta))
                else:
                    arcs.append((end, -delta))

    if not lats:
        raise ValueError("GeoJSON contains no coordinates: {!r}".format(path))

    min_lat, max_lat = min(lats), max(lats)
    if wraps_world:
        return (-_HALF_CIRCLE, min_lat, _HALF_CIRCLE, max_lat)

    min_lon, span = _covering_arc(arcs)
    max_lon = min_lon + span
    if max_lon > _HALF_CIRCLE:
        max_lon -= _FULL_CIRCLE
    return (min_lon, min_lat, max_lon, max_lat)


def _iter_geometries(node: Any) -> Iterator[Dict[str, Any]]:
    """Yield every geometry reachable from a GeoJSON object."""
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    if kind == "FeatureCollection":
        for feature in node.get("features") or ():
            yield from _iter_geometries(feature)
    elif kind == "Feature":
        yield from _iter_geometries(node.get("geometry"))
    elif kind == "GeometryCollection":
        for geometry in node.get("geometries") or ():
            yield from _iter_geometries(geometry)
    elif kind in _GEOMETRY_TYPES:
        yield node


def _iter_paths(geometry: Dict[str, Any]) -> Iterator[Sequence[Position]]:
    """Yield each connected run of positions in a geometry.

    Separate points come out as separate one-position runs: unlike the
    vertices of a line or a ring, nothing spans the gap between them.
    """
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return
    if kind == "Point":
        yield [coordinates]
    elif kind == "MultiPoint":
        for position in coordinates:
            yield [position]
    elif kind == "LineString":
        yield coordinates
    elif kind == "MultiLineString":
        for line in coordinates:
            yield line
    elif kind == "Polygon":
        for ring in coordinates:
            yield _closed(ring)
    elif kind == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield _closed(ring)


def _closed(ring: Sequence[Position]) -> Sequence[Position]:
    """Return a ring whose closing segment is present."""
    if len(ring) > 1 and list(ring[0][:2]) != list(ring[-1][:2]):
        return list(ring) + [ring[0]]
    return ring


def _wrap_lon(lon: float) -> float:
    """Fold a longitude into [-180, 180], leaving in-range values untouched."""
    if -_HALF_CIRCLE <= lon <= _HALF_CIRCLE:
        return lon
    return math.remainder(lon, _FULL_CIRCLE)


def _start_of_box(lon: float) -> float:
    """Fold a box's western edge into [-180, 180)."""
    lon = math.remainder(lon, _FULL_CIRCLE)
    return -_HALF_CIRCLE if lon == _HALF_CIRCLE else lon


def _covering_arc(arcs: Sequence[Arc]) -> Tuple[float, float]:
    """Return the shortest ``(start, span)`` arc covering every input arc.

    The covered longitudes are merged on the circle; what is left over are the
    gaps, and the widest gap is the one worth cutting out.
    """
    spans: List[Tuple[float, float]] = []
    for start, width in arcs:
        if start == _HALF_CIRCLE:  # same meridian as -180, and easier to sort
            start = -_HALF_CIRCLE
        end = start + width
        if end > _HALF_CIRCLE:
            spans.append((start, _HALF_CIRCLE))
            spans.append((-_HALF_CIRCLE, end - _FULL_CIRCLE))
        else:
            spans.append((start, end))
    spans.sort()

    merged: List[List[float]] = []
    for low, high in spans:
        if merged and low <= merged[-1][1]:
            if high > merged[-1][1]:
                merged[-1][1] = high
        else:
            merged.append([low, high])

    # Start from the gap straddling the antimeridian, so that a tie keeps the
    # ordinary min_lon < max_lon form.
    gap_start = merged[-1][1]
    widest = merged[0][0] - merged[-1][1] + _FULL_CIRCLE
    for (_, high), (low, _) in zip(merged, merged[1:]):
        if low - high > widest:
            widest = low - high
            gap_start = high
    return _start_of_box(gap_start + widest), _FULL_CIRCLE - widest
```