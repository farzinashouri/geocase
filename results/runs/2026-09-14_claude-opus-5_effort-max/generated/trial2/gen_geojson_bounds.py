"""Geographic bounding boxes for GeoJSON files.

``geojson_bounds`` reads a GeoJSON document whose coordinates are
longitude/latitude in EPSG:4326 (WGS84) and reports the extent the data really
occupies on the globe.

Longitude is cyclic, so a plain ``min()``/``max()`` over the coordinate values
is wrong for data that straddles the antimeridian: a cluster of islands around
180 deg E would come out as a box spanning almost the whole planet.  Here the
longitudes are treated as arcs on a circle, the widest empty gap between them is
located, and the box is the complement of that gap.  Following RFC 7946 section
5.2, a box crossing the antimeridian is reported with a western edge numerically
greater than its eastern edge -- Fiji is ``(177.0, -20.0, -178.0, -16.0)`` --
which keeps every longitude inside [-180, 180].

Connected runs of vertices (line strings and polygon rings) are unwrapped in
vertex order first, each step taking the shorter way round, so a line that
genuinely runs most of the way around the globe keeps its true span instead of
collapsing onto the short arc.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Iterator, Sequence

__all__ = ["geojson_bounds"]

_CIRCLE = 360.0
_HALF_CIRCLE = 180.0

_GEOMETRY_TYPES = frozenset(
    ("Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon")
)

Arc = tuple[float, float]  # (western edge, eastward length in degrees)
Segment = tuple[float, float]  # (begin, end), both within [0, 360]


def geojson_bounds(path: str | os.PathLike[str]) -> tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    The file may hold a FeatureCollection, a Feature, or a bare geometry
    (including a GeometryCollection); every geometry it contains is taken into
    account.  ``min_lon`` is the western edge of the box and ``max_lon`` the
    eastern one, both in [-180, 180]; when the extent crosses the antimeridian
    ``min_lon > max_lon``.

    Raises ``ValueError`` if the document holds no usable coordinates.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    arcs: list[Arc] = []
    lat_min = math.inf
    lat_max = -math.inf

    for run in _coordinate_runs(document):
        lons: list[float] = []
        for position in run:
            lon, lat = _position(position)
            lons.append(lon)
            lat_min = min(lat_min, lat)
            lat_max = max(lat_max, lat)
        if lons:
            arcs.append(_sweep(lons))

    if not arcs:
        raise ValueError("no coordinates found in GeoJSON document: %r" % (path,))

    lon_min, lon_max = _enclosing_arc(arcs)
    return (lon_min, lat_min, lon_max, lat_max)


def _coordinate_runs(document: object) -> Iterator[Sequence[object]]:
    """Yield each connected run of positions in the document.

    A run is a sequence of positions joined by edges -- a line string, or one
    polygon ring.  Isolated positions (points, and the members of a multipoint)
    are yielded as one-element runs, since nothing connects them.
    """
    for geometry in _geometries(document):
        coordinates = geometry.get("coordinates")
        if not coordinates:
            continue
        kind = geometry.get("type")
        if kind == "Point":
            yield [coordinates]
        elif kind == "MultiPoint":
            for position in coordinates:
                yield [position]
        elif kind == "LineString":
            yield coordinates
        elif kind in ("MultiLineString", "Polygon"):
            yield from coordinates
        elif kind == "MultiPolygon":
            for polygon in coordinates:
                yield from polygon


def _geometries(node: object) -> Iterator[dict]:
    """Yield every geometry object reachable from a GeoJSON node."""
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    if kind == "FeatureCollection":
        for feature in node.get("features") or ():
            yield from _geometries(feature)
    elif kind == "Feature":
        yield from _geometries(node.get("geometry"))
    elif kind == "GeometryCollection":
        for geometry in node.get("geometries") or ():
            yield from _geometries(geometry)
    elif kind in _GEOMETRY_TYPES:
        yield node


def _position(position: object) -> tuple[float, float]:
    """Return ``(lon, lat)`` from a GeoJSON position, ignoring any elevation."""
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        raise ValueError("malformed GeoJSON position: %r" % (position,))
    return float(position[0]), float(position[1])


def _sweep(lons: Sequence[float]) -> Arc:
    """Return the arc swept by one connected run of longitudes.

    Consecutive vertices are joined the shorter way round -- a step of more than
    180 deg is read as a crossing of the antimeridian -- and the running offset
    from the first vertex is tracked, so a run that circles the globe keeps its
    full span instead of folding onto itself.
    """
    start = _wrap(lons[0])
    offset = lowest = highest = 0.0
    previous = start
    for lon in lons[1:]:
        current = _wrap(lon)
        offset += _wrap(current - previous)
        lowest = min(lowest, offset)
        highest = max(highest, offset)
        previous = current
    return start + lowest, highest - lowest


def _enclosing_arc(arcs: Sequence[Arc]) -> tuple[float, float]:
    """Return the (west, east) edges of the narrowest arc covering every arc."""
    segments: list[Segment] = []
    for start, length in arcs:
        if length >= _CIRCLE:
            return -_HALF_CIRCLE, _HALF_CIRCLE
        begin = start % _CIRCLE
        end = begin + length
        if end > _CIRCLE:  # split the wrap-around so segments stay in [0, 360]
            segments.append((begin, _CIRCLE))
            segments.append((0.0, end - _CIRCLE))
        else:
            segments.append((begin, end))

    segments.sort()
    merged: list[Segment] = [segments[0]]
    for begin, end in segments[1:]:
        last_begin, last_end = merged[-1]
        if begin <= last_end:
            merged[-1] = (last_begin, max(last_end, end))
        else:
            merged.append((begin, end))

    # The box is the complement of the widest gap between the covered segments.
    # Start from the gap across the 0/360 seam so that ties favour a box which
    # does not cross the antimeridian.
    west = merged[0][0]
    widest = merged[0][0] + _CIRCLE - merged[-1][1]
    for left, right in zip(merged, merged[1:]):
        gap = right[0] - left[1]
        if gap > widest:
            widest = gap
            west = right[0]

    if widest <= 0.0:  # every longitude is covered
        return -_HALF_CIRCLE, _HALF_CIRCLE

    west = _wrap(west)
    east = west + (_CIRCLE - widest)
    if east > _HALF_CIRCLE:
        east -= _CIRCLE
    return west, east


def _wrap(lon: float) -> float:
    """Fold a longitude, or a longitude difference, into [-180, 180)."""
    return (lon + _HALF_CIRCLE) % _CIRCLE - _HALF_CIRCLE