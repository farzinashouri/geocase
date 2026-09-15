"""Compute the true geographic bounding box of a GeoJSON file.

The module reads a GeoJSON document whose coordinates are longitude/latitude
in EPSG:4326 and returns the extent of its features as
``(min_lon, min_lat, max_lon, max_lat)``.

Longitudes live on a circle, so the naive ``min()``/``max()`` of the raw
coordinate values is wrong for anything that crosses the antimeridian: a
geometry running from 179 deg E to 179 deg W would come out as a box spanning
almost the whole planet instead of the two-degree sliver it really occupies.

This implementation therefore works on the circle:

* Each connected coordinate sequence (line, ring, ...) is "unwrapped": every
  step between consecutive vertices is taken along the shorter way around, so
  a sequence that walks over the antimeridian yields a continuous, possibly
  out-of-range run of longitudes whose span is its real angular width.
* Every geometry contributes one or more arcs on the longitude circle. The
  arcs are unioned, the widest uncovered gap is found, and the bounding box is
  the complement of that gap -- the narrowest arc containing all the data.

Following RFC 7946 section 5.2, a box that crosses the antimeridian is
reported with ``min_lon > max_lon`` (e.g. ``(170.0, ..., -170.0, ...)``).
Output longitudes are always within ``[-180, 180]``.
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

_FULL_CIRCLE = 360.0


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` is anything ``open()`` accepts. The file must contain a
    FeatureCollection, Feature, Geometry or GeometryCollection with
    EPSG:4326 coordinates.

    Raises:
        ValueError: the document holds no coordinates, or an unknown
            geometry type.
    """
    with open(path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)

    arcs: List[Tuple[float, float]] = []  # (start_lon, width) on the circle
    min_lat = math.inf
    max_lat = -math.inf

    for geometry in _iter_geometries(doc):
        for sequence in _coordinate_sequences(geometry):
            lons, lats = _unwrap(sequence)
            if not lons:
                continue
            arcs.append((lons[0] if len(lons) == 1 else min(lons),
                         max(lons) - min(lons)))
            min_lat = min(min_lat, min(lats))
            max_lat = max(max_lat, max(lats))

    if not arcs:
        raise ValueError("GeoJSON document contains no coordinates")

    min_lon, max_lon = _circular_extent(arcs)
    return (min_lon, min_lat, max_lon, max_lat)


def _iter_geometries(node: Any) -> Iterator[dict]:
    """Yield every geometry object reachable from a GeoJSON node."""
    if not isinstance(node, dict):
        return
    node_type = node.get("type")
    if node_type == "FeatureCollection":
        for feature in node.get("features") or []:
            yield from _iter_geometries(feature)
    elif node_type == "Feature":
        yield from _iter_geometries(node.get("geometry"))
    elif node_type == "GeometryCollection":
        for geometry in node.get("geometries") or []:
            yield from _iter_geometries(geometry)
    elif node_type is not None:
        yield node


def _coordinate_sequences(geometry: dict) -> Iterator[Sequence[Sequence[float]]]:
    """Yield the connected coordinate runs of a geometry.

    Vertices within one yielded run are assumed to be joined by edges taking
    the short way around the globe; separate runs are independent.
    """
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        return

    if geometry_type == "Point":
        yield [coordinates]
    elif geometry_type in ("MultiPoint",):
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
    else:
        raise ValueError("unsupported geometry type: %r" % (geometry_type,))


def _normalize_lon(lon: float) -> float:
    """Fold a longitude into ``[-180, 180]``."""
    return math.remainder(float(lon), _FULL_CIRCLE)


def _unwrap(sequence: Sequence[Sequence[float]]) -> Tuple[List[float], List[float]]:
    """Return continuous longitudes and plain latitudes for one run.

    Each step is taken along the shorter arc, so the returned longitudes may
    leave ``[-180, 180]`` but their span is the run's real angular width.
    """
    lons: List[float] = []
    lats: List[float] = []
    previous_raw = None
    current = 0.0

    for position in sequence:
        raw = _normalize_lon(position[0])
        if previous_raw is None:
            current = raw
        else:
            current += math.remainder(raw - previous_raw, _FULL_CIRCLE)
        previous_raw = raw
        lons.append(current)
        lats.append(float(position[1]))

    return lons, lats


def _circular_extent(arcs: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Reduce arcs to the narrowest containing arc, as ``(min_lon, max_lon)``.

    Arcs are given as ``(start_lon, width)``. Work happens in a ``[0, 360)``
    domain (``lon + 180``) so the wrap point is at the ends of the interval.
    """
    segments: List[Tuple[float, float]] = []
    for start, width in arcs:
        if width >= _FULL_CIRCLE:
            return (-180.0, 180.0)
        begin = (_normalize_lon(start) + 180.0) % _FULL_CIRCLE
        end = begin + width
        if end <= _FULL_CIRCLE:
            segments.append((begin, end))
        else:
            segments.append((begin, _FULL_CIRCLE))
            segments.append((0.0, end - _FULL_CIRCLE))

    segments.sort()
    merged: List[List[float]] = [list(segments[0])]
    for begin, end in segments[1:]:
        if begin <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([begin, end])

    # The bounding arc is the complement of the widest uncovered gap. The gap
    # that wraps past 360 corresponds to the ordinary, non-crossing case.
    widest_gap = (merged[0][0] + _FULL_CIRCLE) - merged[-1][1]
    box_begin, box_end = merged[0][0], merged[-1][1]
    for earlier, later in zip(merged, merged[1:]):
        gap = later[0] - earlier[1]
        if gap > widest_gap:
            widest_gap = gap
            box_begin, box_end = later[0], earlier[1] + _FULL_CIRCLE

    if widest_gap <= 0.0:
        return (-180.0, 180.0)

    return (_normalize_lon(box_begin - 180.0), _normalize_lon(box_end - 180.0))