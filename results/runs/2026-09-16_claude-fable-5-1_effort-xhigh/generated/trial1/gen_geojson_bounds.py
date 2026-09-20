"""Bounding box of a GeoJSON file in EPSG:4326 (WGS84).

The single public function, :func:`geojson_bounds`, returns the extent of all
features in a file as ``(min_lon, min_lat, max_lon, max_lat)``.  Unlike a plain
min/max over the raw coordinates, the box describes where the geometry really
lies on the globe:

* Longitudes outside ``[-180, 180]`` in the input are wrapped into that range.
* Neighbouring vertices of a line or ring that are more than 180 degrees apart
  are taken to cross the antimeridian.  A box that crosses the antimeridian is
  expressed as in RFC 7946 section 5.2: ``min_lon`` is greater than ``max_lon``
  and every longitude stays inside ``[-180, 180]``.
* A polygon ring that winds all the way around the globe encloses a pole, so
  the latitude range is extended to that pole.

Only the standard library is used.  Importing the module has no side effects.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

__all__ = ["geojson_bounds"]

_SIMPLE_GEOMETRIES = frozenset(
    {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}
)
_EPS = 1e-9


def geojson_bounds(path: str | os.PathLike[str]) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` may point at a FeatureCollection, a Feature or a bare geometry.
    Coordinates must be longitude/latitude in EPSG:4326.  If the data crosses
    the antimeridian the returned ``min_lon`` is greater than ``max_lon``.

    Raises ``ValueError`` when the file contains no coordinates at all.
    """
    with open(os.fspath(path), "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    arcs: List[Tuple[float, float]] = []
    lat_min = math.inf
    lat_max = -math.inf
    for geometry in _iter_geometries(data):
        for positions, is_ring in _iter_parts(geometry):
            extent = _part_extent(positions, is_ring)
            if extent is None:
                continue
            lon_start, lon_end, part_lat_min, part_lat_max = extent
            arcs.append((lon_start, lon_end))
            lat_min = min(lat_min, part_lat_min)
            lat_max = max(lat_max, part_lat_max)

    if not arcs:
        raise ValueError(f"{os.fspath(path)}: no coordinates found")

    min_lon, max_lon = _combine_lon(arcs)
    return float(min_lon), float(lat_min), float(max_lon), float(lat_max)


def _wrap_lon(lon: float) -> float:
    """Wrap ``lon`` into [-180, 180]; values already in range are left untouched."""
    if -180.0 <= lon <= 180.0:
        return lon
    return (lon + 180.0) % 360.0 - 180.0


def _iter_geometries(obj: Any) -> Iterator[Dict[str, Any]]:
    """Yield every concrete geometry object reachable from a GeoJSON object."""
    if not isinstance(obj, dict):
        return
    kind = obj.get("type")
    if kind == "FeatureCollection":
        for feature in obj.get("features") or ():
            yield from _iter_geometries(feature)
    elif kind == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif kind == "GeometryCollection":
        for geometry in obj.get("geometries") or ():
            yield from _iter_geometries(geometry)
    elif kind in _SIMPLE_GEOMETRIES:
        yield obj


def _iter_parts(geometry: Dict[str, Any]) -> Iterator[Tuple[Sequence[Any], bool]]:
    """Yield ``(positions, is_ring)`` for every connected piece of a geometry.

    Points are yielded one at a time so unrelated points are never read as a
    path.  Lines and rings keep their vertex order so that antimeridian
    crossings between neighbouring vertices can be recognised.
    """
    coords = geometry.get("coordinates")
    if not coords:
        return
    kind = geometry["type"]
    if kind == "Point":
        yield (coords,), False
    elif kind == "MultiPoint":
        for position in coords:
            yield (position,), False
    elif kind == "LineString":
        yield coords, False
    elif kind == "MultiLineString":
        for line in coords:
            yield line, False
    elif kind == "Polygon":
        for ring in coords:
            yield ring, True
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield ring, True


def _part_extent(
    positions: Sequence[Any], is_ring: bool
) -> Optional[Tuple[float, float, float, float]]:
    """Extent of one connected part, or ``None`` if it has no usable positions.

    Returns ``(lon_start, lon_end, lat_min, lat_max)``.  Longitudes are
    unwrapped along the vertex order, each step taking the shorter way around
    the globe, so ``lon_start`` lies in [-180, 180] and ``lon_end - lon_start``
    is the angular width of the part (at most 360).
    """
    lons: List[float] = []
    lats: List[float] = []
    for position in positions:
        if position is None or len(position) < 2:
            continue
        lons.append(_wrap_lon(float(position[0])))
        lats.append(float(position[1]))
    if not lons:
        return None

    # Close rings so that a full turn around a pole is counted completely.
    walk = lons + lons[:1] if is_ring else lons
    unwrapped = [walk[0]]
    for prev, cur in zip(walk, walk[1:]):
        step = cur - prev
        if step > 180.0:
            step -= 360.0
        elif step < -180.0:
            step += 360.0
        unwrapped.append(unwrapped[-1] + step)

    lo, hi = min(unwrapped), max(unwrapped)
    lat_min, lat_max = min(lats), max(lats)

    if is_ring and abs(unwrapped[-1] - unwrapped[0]) >= 360.0 - _EPS:
        # The ring winds fully around the globe, so it encloses the nearer pole.
        if lat_min + lat_max >= 0.0:
            lat_max = 90.0
        else:
            lat_min = -90.0

    start = _wrap_lon(lo)
    if start == 180.0 and hi > lo:
        start = -180.0
    end = hi + (start - lo)
    return start, end, lat_min, lat_max


def _combine_lon(arcs: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Combine longitude arcs into ``(min_lon, max_lon)``.

    Each arc is ``(start, end)`` with ``start`` in [-180, 180] and a width
    ``end - start`` in [0, 360].  When nothing straddles the antimeridian the
    result is the ordinary min/max.  Otherwise the narrowest arc that covers
    all the data is returned, with ``min_lon > max_lon`` marking the crossing.
    """
    merged: List[List[float]] = []
    for start, end in sorted(arcs):
        if end - start >= 360.0 - _EPS:
            return -180.0, 180.0
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # An arc running past 180 may swallow arcs at the front of the list once
    # those are shifted forward by a full turn.
    while len(merged) > 1 and merged[-1][1] >= merged[0][0] + 360.0:
        merged[-1][1] = max(merged[-1][1], merged[0][1] + 360.0)
        merged.pop(0)

    if merged[-1][1] <= 180.0:
        # Nothing straddles the antimeridian: the plain min/max box is right.
        return merged[0][0], merged[-1][1]

    # The antimeridian is covered, so the box is the complement of the largest
    # gap between the merged arcs.
    count = len(merged)
    best_gap, best_index = -1.0, 0
    for index in range(count):
        following = merged[(index + 1) % count][0]
        if index == count - 1:
            following += 360.0
        gap = following - merged[index][1]
        if gap > best_gap:
            best_gap, best_index = gap, index
    if best_gap <= _EPS:
        return -180.0, 180.0

    min_lon = merged[(best_index + 1) % count][0]
    if min_lon == 180.0:
        min_lon = -180.0
    max_lon = merged[best_index][1]
    while max_lon > 180.0:
        max_lon -= 360.0
    return min_lon, max_lon