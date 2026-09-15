```python
"""Bounding boxes for GeoJSON files whose coordinates are EPSG:4326 (WGS84).

The only public entry point is :func:`geojson_bounds`.

Antimeridian handling
---------------------
Longitude is an angle on a circle, not a value on the real line, so the
naive ``min()``/``max()`` over every coordinate in a file is wrong near
180 degrees: a small polygon straddling the antimeridian (Fiji, say, at
177E .. 177W) comes out as a box 354 degrees wide, which is not the
actual extent of the geometry on Earth.

This module instead computes the *narrowest* longitude interval that
covers the whole geometry, and reports it following RFC 7946 section 5.2:
when that interval crosses the antimeridian, the returned box has
``min_lon > max_lon``.  Every returned longitude stays within
[-180, 180]; input longitudes outside that range (e.g. 185) are wrapped
back into it first.

Within a connected coordinate sequence (a LineString, or a polygon ring)
a step of more than 180 degrees of longitude between neighbouring
vertices is read as a crossing of the antimeridian rather than as a trip
the long way around the globe.
"""

from __future__ import annotations

import json
from typing import Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

_FULL = 360.0
# Slack used when joining longitude intervals, in degrees.  Well below any
# meaningful geographic resolution (~0.1 micrometre at the equator), but
# large enough to absorb floating-point noise from the wrapping above.
_TOL = 1e-9

_GEOMETRY_TYPES = frozenset(
    (
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    )
)


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` is anything :func:`open` accepts.  The file may hold a
    FeatureCollection, a Feature, a GeometryCollection or a bare geometry.

    Longitudes are always within [-180, 180].  If the tightest box around
    the data crosses the antimeridian, ``min_lon > max_lon`` (RFC 7946
    section 5.2) -- the box then runs east from ``min_lon``, over 180, to
    ``max_lon``.

    Raises ``ValueError`` if the file is not GeoJSON this module
    understands, or if it holds no coordinates at all.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    arcs: List[Tuple[float, float]] = []
    min_lat = float("inf")
    max_lat = float("-inf")

    for geometry in _iter_geometries(document):
        for part in _iter_parts(geometry):
            if not part:
                continue
            lon_lo, lon_hi, lat_lo, lat_hi = _part_extent(part)
            arcs.append((lon_lo, lon_hi))
            if lat_lo < min_lat:
                min_lat = lat_lo
            if lat_hi > max_lat:
                max_lat = lat_hi

    if not arcs:
        raise ValueError("GeoJSON document contains no coordinates")

    min_lon, max_lon = _covering_arc(arcs)
    return (min_lon, min_lat, max_lon, max_lat)


def _iter_geometries(node) -> Iterator[dict]:
    """Yield every non-null geometry object reachable from ``node``."""
    if not isinstance(node, dict):
        raise ValueError("expected a GeoJSON object, got %s" % type(node).__name__)

    node_type = node.get("type")
    if node_type == "FeatureCollection":
        for feature in node.get("features") or ():
            yield from _iter_geometries(feature)
    elif node_type == "Feature":
        geometry = node.get("geometry")
        if geometry is not None:
            yield from _iter_geometries(geometry)
    elif node_type == "GeometryCollection":
        for geometry in node.get("geometries") or ():
            yield from _iter_geometries(geometry)
    elif node_type in _GEOMETRY_TYPES:
        yield node
    else:
        raise ValueError("unsupported GeoJSON type: %r" % (node_type,))


def _iter_parts(geometry: dict) -> Iterator[Sequence]:
    """Yield the geometry's coordinate sequences.

    Each yielded sequence is *connected*: consecutive positions in it are
    joined by an edge, which is what lets :func:`_part_extent` tell an
    antimeridian crossing from a jump to the far side of the world.  The
    points of a MultiPoint share no edges, so each is its own part.
    """
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return

    if geometry_type == "Point":
        yield [coordinates]
    elif geometry_type == "MultiPoint":
        for position in coordinates:
            yield [position]
    elif geometry_type == "LineString":
        yield coordinates
    elif geometry_type in ("MultiLineString", "Polygon"):
        for part in coordinates:
            yield part
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield ring


def _part_extent(part: Sequence) -> Tuple[float, float, float, float]:
    """Return ``(lon_lo, lon_hi, lat_lo, lat_hi)`` for one coordinate sequence.

    The longitudes are *unwrapped*: they are made continuous along the
    sequence, so ``lon_hi`` may exceed 180 (or ``lon_lo`` fall below -180)
    for a part that crosses the antimeridian.  A part that winds right
    around the Earth -- a ring enclosing a pole, say -- ends up with
    ``lon_hi - lon_lo >= 360``.
    """
    lon, lat = _position(part[0])
    lon_lo = lon_hi = lon
    lat_lo = lat_hi = lat
    previous = lon

    for position in part[1:]:
        lon, lat = _position(position)
        # Step to the nearest image of this longitude, i.e. take the
        # shorter of the two ways round the circle.
        step = ((lon - previous) + 180.0) % _FULL - 180.0
        previous = previous + step

        if previous < lon_lo:
            lon_lo = previous
        elif previous > lon_hi:
            lon_hi = previous
        if lat < lat_lo:
            lat_lo = lat
        elif lat > lat_hi:
            lat_hi = lat

    return (lon_lo, lon_hi, lat_lo, lat_hi)


def _position(position) -> Tuple[float, float]:
    """Return ``(lon, lat)`` from a GeoJSON position, ignoring any altitude."""
    try:
        lon = float(position[0])
        lat = float(position[1])
    except (TypeError, ValueError, IndexError, KeyError):
        raise ValueError("invalid GeoJSON position: %r" % (position,)) from None
    return (_wrap_lon(lon), lat)


def _wrap_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    lon = (lon + 180.0) % _FULL - 180.0
    if lon >= 180.0:  # only reachable through floating-point rounding
        lon -= _FULL
    return lon


def _covering_arc(arcs: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Return ``(min_lon, max_lon)`` of the narrowest arc covering ``arcs``.

    The narrowest covering arc is the complement of the widest gap the
    data leaves uncovered, so the work is a circular interval merge.
    Intervals are handled in "turn" coordinates ``u = lon + 180`` on
    [0, 360], where an arc crossing the antimeridian is the one that
    wraps past 360.
    """
    segments: List[Tuple[float, float]] = []
    for lon_lo, lon_hi in arcs:
        width = lon_hi - lon_lo
        if width >= _FULL - _TOL:
            return (-180.0, 180.0)
        start = _wrap_lon(lon_lo) + 180.0
        end = start + width
        if end <= _FULL:
            segments.append((start, end))
        else:  # split the wrapping arc at the antimeridian
            segments.append((start, _FULL))
            segments.append((0.0, end - _FULL))

    segments.sort()
    merged: List[List[float]] = []
    for start, end in segments:
        if merged and start <= merged[-1][1] + _TOL:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])

    count = len(merged)
    widest_gap = -1.0
    gap_index = 0
    for index in range(count):
        gap = merged[(index + 1) % count][0] - merged[index][1]
        if index == count - 1:
            gap += _FULL  # the gap that wraps back round to the first interval
        if gap > widest_gap:
            widest_gap = gap
            gap_index = index

    if widest_gap <= _TOL:  # the data covers every longitude
        return (-180.0, 180.0)

    min_lon = merged[(gap_index + 1) % count][0] - 180.0
    max_lon = merged[gap_index][1] - 180.0
    return (_clamp_lon(min_lon), _clamp_lon(max_lon))


def _clamp_lon(lon: float) -> float:
    """Pin a longitude to [-180, 180], absorbing floating-point overshoot."""
    if lon < -180.0:
        return -180.0
    if lon > 180.0:
        return 180.0
    return lon
```