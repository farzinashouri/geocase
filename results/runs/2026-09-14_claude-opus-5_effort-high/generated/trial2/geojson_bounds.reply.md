Longitude is circular, so the only way to report a true extent for antimeridian-crossing data with both longitudes in `[-180, 180]` is the RFC 7946 §5.2 convention (`min_lon > max_lon`); the module finds the narrowest covering arc rather than taking a naive min/max.

```python
"""Bounding box of a GeoJSON file in EPSG:4326 (WGS84).

Longitude is a circular quantity, so a plain ``min``/``max`` over the raw
coordinates reports a near-global extent for anything that straddles the
antimeridian.  This module instead computes the *narrowest* longitude arc that
contains the data, which is the extent the geometry actually occupies on Earth.

Every segment between two consecutive vertices is taken to follow the shorter
of the two arcs between them; a jump of more than 180 degrees therefore means
the segment crosses the antimeridian.  Following RFC 7946 section 5.2, a box
whose longitude arc crosses the antimeridian is reported with
``min_lon > max_lon`` -- that is the only way to describe such an extent while
keeping both longitudes inside ``[-180, 180]``, as required.

Latitudes are taken verbatim: containment of a pole is not inferred from a
polygon's winding.
"""

from __future__ import annotations

import json
import os
from typing import Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

# Tolerance (degrees) used when deciding whether two longitude arcs touch.
_EPS = 1e-9

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

# A longitude arc, expressed in the shifted space x = lon + 180 (so x runs over
# [0, 360]) together with the original longitudes of its two endpoints, which
# are what we hand back to the caller.
_Arc = Tuple[float, float, float, float]


def geojson_bounds(
    path: "str | os.PathLike[str]",
) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` may point at a FeatureCollection, a Feature, or a bare geometry.
    If the geometry crosses the antimeridian the returned ``min_lon`` is
    greater than ``max_lon`` (RFC 7946 section 5.2); both are always within
    ``[-180, 180]``.

    Raises ``ValueError`` if the document holds no coordinates or is not
    recognisable GeoJSON.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    lats: List[float] = []
    arcs: List[_Arc] = []
    for run in _iter_runs(document):
        if not run:
            continue
        lats.extend(lat for _, lat in run)
        if len(run) == 1:
            lon = run[0][0]
            arcs.extend(_arc(lon, lon))
        else:
            for (lon_a, _), (lon_b, _) in zip(run, run[1:]):
                arcs.extend(_arc(lon_a, lon_b))

    if not lats:
        raise ValueError(f"no coordinates found in {os.fspath(path)!r}")

    min_lon, max_lon = _longitude_extent(arcs)
    return (min_lon, min(lats), max_lon, max(lats))


def _iter_runs(node: object) -> Iterator[List[Tuple[float, float]]]:
    """Yield connected vertex runs: consecutive vertices share an edge.

    Isolated positions (a Point, each member of a MultiPoint) come back as
    single-element runs, which constrain the box without contributing an edge.
    """
    if not isinstance(node, dict):
        raise ValueError(f"expected a GeoJSON object, got {type(node).__name__}")

    kind = node.get("type")
    if kind == "FeatureCollection":
        for feature in node.get("features") or []:
            yield from _iter_runs(feature)
    elif kind == "Feature":
        geometry = node.get("geometry")
        if geometry is not None:
            yield from _iter_runs(geometry)
    elif kind == "GeometryCollection":
        for geometry in node.get("geometries") or []:
            yield from _iter_runs(geometry)
    elif kind in _GEOMETRY_TYPES:
        coordinates = node.get("coordinates")
        if coordinates:
            yield from _geometry_runs(kind, coordinates)
    elif kind is None:
        raise ValueError('GeoJSON object is missing its "type" member')
    else:
        raise ValueError(f"unsupported GeoJSON type: {kind!r}")


def _geometry_runs(
    kind: str, coordinates: Sequence
) -> Iterator[List[Tuple[float, float]]]:
    if kind == "Point":
        yield [_position(coordinates)]
    elif kind == "MultiPoint":
        for position in coordinates:
            yield [_position(position)]
    elif kind == "LineString":
        yield [_position(position) for position in coordinates]
    elif kind == "MultiLineString":
        for line in coordinates:
            yield [_position(position) for position in line]
    elif kind == "Polygon":
        for ring in coordinates:
            yield _closed_ring(ring)
    elif kind == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield _closed_ring(ring)


def _closed_ring(ring: Sequence) -> List[Tuple[float, float]]:
    vertices = [_position(position) for position in ring]
    if vertices and vertices[0] != vertices[-1]:
        vertices.append(vertices[0])
    return vertices


def _position(position: Sequence) -> Tuple[float, float]:
    """Return ``(lon, lat)``, dropping any elevation and wrapping longitude."""
    try:
        lon = float(position[0])
        lat = float(position[1])
    except (TypeError, IndexError, ValueError, KeyError) as exc:
        raise ValueError(f"malformed GeoJSON position: {position!r}") from exc
    return _wrap_lon(lon), lat


def _wrap_lon(lon: float) -> float:
    """Fold a longitude into [-180, 180], leaving in-range values untouched."""
    if -180.0 <= lon <= 180.0:
        return lon
    return ((lon + 180.0) % 360.0) - 180.0


def _arc(lon_a: float, lon_b: float) -> List[_Arc]:
    """Longitude arc swept when travelling from ``lon_a`` to ``lon_b``."""
    difference = lon_b - lon_a

    # -180 and +180 name the same meridian, so a segment between them is the
    # full sweep (reading it as the shorter arc would make it degenerate).
    if abs(difference) >= 360.0 - _EPS:
        return [(0.0, 360.0, -180.0, 180.0)]

    if abs(difference) <= 180.0:
        west, east = (lon_a, lon_b) if lon_a <= lon_b else (lon_b, lon_a)
        return [(west + 180.0, east + 180.0, west, east)]

    # Longer than half the globe the direct way, so the segment crosses the
    # antimeridian: it runs east from the larger longitude round to the smaller.
    start, end = max(lon_a, lon_b), min(lon_a, lon_b)
    return [
        (start + 180.0, 360.0, start, 180.0),
        (0.0, end + 180.0, -180.0, end),
    ]


def _longitude_extent(arcs: Sequence[_Arc]) -> Tuple[float, float]:
    """Narrowest longitude interval covering every arc, as ``(min, max)``.

    The covered arcs are merged, the widest uncovered gap is located, and the
    answer is that gap's complement.
    """
    merged: List[List[float]] = []
    for start, end, start_lon, end_lon in sorted(arcs):
        if merged and start <= merged[-1][1] + _EPS:
            if end > merged[-1][1]:
                merged[-1][1] = end
                merged[-1][3] = end_lon
        else:
            merged.append([start, end, start_lon, end_lon])

    count = len(merged)
    widest_gap = -1.0
    before_gap = 0
    for index in range(count):
        following = merged[(index + 1) % count]
        gap = following[0] - merged[index][1]
        if index == count - 1:
            gap += 360.0
        if gap > widest_gap:
            widest_gap = gap
            before_gap = index

    if widest_gap <= _EPS:  # the data wraps all the way round the globe
        return (-180.0, 180.0)

    return (merged[(before_gap + 1) % count][2], merged[before_gap][3])
```