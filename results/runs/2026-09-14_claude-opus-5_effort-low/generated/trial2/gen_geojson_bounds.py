"""Bounding box of a GeoJSON file whose coordinates are lon/lat (EPSG:4326).

The returned box describes the true extent of the data on the sphere: for
geometry that straddles the antimeridian the box is the *short* way around,
so ``min_lon`` may be numerically greater than ``max_lon`` (the convention of
RFC 7946 section 5.2).  All longitudes stay inside [-180, 180].
"""

from __future__ import annotations

import json
from numbers import Real
from typing import Any, Iterator, List, Tuple

__all__ = ["geojson_bounds"]


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Raises ValueError if the file contains no positions.
    """
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    lons: List[float] = []
    lats: List[float] = []
    for lon, lat in _positions(doc):
        lons.append(_wrap_lon(float(lon)))
        lats.append(float(lat))

    if not lons:
        raise ValueError("GeoJSON contains no coordinates")

    min_lon, max_lon = _lon_extent(lons)
    return (min_lon, min(lats), max_lon, max(lats))


# --- traversal ------------------------------------------------------------


def _positions(node: Any) -> Iterator[Tuple[float, float]]:
    """Yield every (lon, lat) position in any GeoJSON object."""
    if isinstance(node, dict):
        gtype = node.get("type")
        if gtype == "FeatureCollection":
            for feature in node.get("features") or ():
                yield from _positions(feature)
        elif gtype == "Feature":
            yield from _positions(node.get("geometry"))
        elif gtype == "GeometryCollection":
            for geom in node.get("geometries") or ():
                yield from _positions(geom)
        elif "coordinates" in node:
            yield from _coords(node["coordinates"])
    elif isinstance(node, list):
        # Bare list of features/geometries.
        for item in node:
            yield from _positions(item)


def _coords(node: Any) -> Iterator[Tuple[float, float]]:
    """Yield positions from an arbitrarily nested ``coordinates`` value."""
    if not isinstance(node, (list, tuple)) or not node:
        return
    head = node[0]
    if isinstance(head, Real) and not isinstance(head, bool):
        if len(node) >= 2 and isinstance(node[1], Real):
            yield (node[0], node[1])
        return
    for item in node:
        yield from _coords(item)


# --- longitude handling ---------------------------------------------------


def _wrap_lon(lon: float) -> float:
    """Normalise a longitude into [-180, 180]."""
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = (lon + 180.0) % 360.0 - 180.0
    # ``%`` maps exactly 180 to -180; keep the positive pole for +180 inputs.
    if wrapped == -180.0 and lon > 0:
        return 180.0
    return wrapped


def _lon_extent(lons: List[float]) -> Tuple[float, float]:
    """Smallest arc on the longitude circle containing every value.

    Found by locating the widest empty gap between consecutive longitudes
    (wrapping around ±180) and taking its complement.
    """
    ordered = sorted(set(lons))
    if len(ordered) == 1:
        return (ordered[0], ordered[0])

    # Gap between each pair, plus the gap that spans the antimeridian.
    best_gap = ordered[0] - ordered[-1] + 360.0
    start, end = ordered[0], ordered[-1]  # arc after the wrap-around gap
    for lo, hi in zip(ordered, ordered[1:]):
        gap = hi - lo
        if gap > best_gap:
            best_gap = gap
            start, end = hi, lo  # arc runs hi -> ... -> lo across ±180

    return (start, end)