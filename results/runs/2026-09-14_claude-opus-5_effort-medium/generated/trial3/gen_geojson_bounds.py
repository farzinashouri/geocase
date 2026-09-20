"""Bounding boxes for GeoJSON files whose coordinates are EPSG:4326 lon/lat.

The only public entry point is :func:`geojson_bounds`.  Importing the module has
no side effects.

The interesting part of the problem is longitude.  Latitude lives on a bounded
interval, so its extent is just ``min``/``max``.  Longitude lives on a circle,
so "the extent of the geometry" is the *shortest arc* that contains all of it,
not the numeric span of the coordinate values.  A polygon around Fiji with
vertices at 179.9 and -179.9 covers 0.2 degrees of the Earth, not 359.8, and its
bounding box is ``(179.9, ..., -179.9, ...)`` -- i.e. ``min_lon > max_lon``,
which is how RFC 7946 section 5.2 encodes a box that crosses the antimeridian.
Output longitudes are always normalized into ``[-180, 180]``.

Method:

* Each connected path (a LineString, a polygon ring, ...) is unwrapped so that
  successive vertices differ by less than 180 degrees, following RFC 7946's rule
  that an edge takes the short way around.  That gives one arc per path.
* Isolated points contribute zero-width arcs.
* The arcs are merged on the circle.  If the merged coverage is a single arc,
  that is the answer; otherwise the components are joined across every gap but
  the largest one, which yields the shortest arc containing everything.
"""

from __future__ import annotations

import bisect
import json
from typing import Iterable, Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

# Tolerance used when merging arcs and when snapping results back onto observed
# input values.  Roughly a tenth of a millimetre at the equator.
_EPS = 1e-9
_SNAP = 1e-7

_MULTIPART = {"MultiLineString", "Polygon"}


def _wrap180(lon: float) -> float:
    """Normalize a longitude into ``[-180, 180)``."""
    return ((float(lon) + 180.0) % 360.0) - 180.0


def _shortest_delta(a: float, b: float) -> float:
    """Signed difference ``b - a`` taken the short way around the circle."""
    d = (float(b) - float(a) + 180.0) % 360.0 - 180.0
    # ``%`` maps an exact half-turn onto -180; either sign is arbitrary there.
    return d


def _geometries(obj: dict) -> Iterator[dict]:
    """Yield every geometry object contained in a GeoJSON object."""
    if not isinstance(obj, dict):
        raise ValueError("GeoJSON object must be a JSON object")
    kind = obj.get("type")
    if kind == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _geometries(feature)
    elif kind == "Feature":
        geometry = obj.get("geometry")
        if geometry is not None:
            yield from _geometries(geometry)
    elif kind is None:
        raise ValueError("GeoJSON object has no 'type' member")
    else:
        yield obj


def _paths(geom: dict) -> Iterator[Sequence[Sequence[float]]]:
    """Yield each connected run of positions in a geometry.

    Points and the members of a MultiPoint are yielded as one-position paths,
    since they are not joined to anything by an edge.
    """
    kind = geom.get("type")
    if kind == "GeometryCollection":
        for sub in geom.get("geometries") or []:
            yield from _paths(sub)
        return

    coords = geom.get("coordinates")
    if not coords:
        return

    if kind == "Point":
        yield [coords]
    elif kind == "MultiPoint":
        for position in coords:
            yield [position]
    elif kind == "LineString":
        yield coords
    elif kind in _MULTIPART:
        for part in coords:
            if part:
                yield part
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon or []:
                if ring:
                    yield ring
    else:
        raise ValueError("unsupported geometry type: %r" % (kind,))


def _arc(lons: Iterable[float]) -> Tuple[float, float]:
    """Return ``(start, width)`` of the arc swept by one connected path.

    ``start`` is normalized into ``[-180, 180)``; ``width`` is in ``[0, 360]``.
    """
    it = iter(lons)
    base = _wrap180(next(it))
    low = high = 0.0
    current = 0.0
    previous = base
    for lon in it:
        lon = _wrap180(lon)
        current += _shortest_delta(previous, lon)
        previous = lon
        if current < low:
            low = current
        elif current > high:
            high = current
    width = high - low
    if width >= 360.0:
        return (-180.0, 360.0)
    return (_wrap180(base + low), width)


def _merge(arcs: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Merge arcs, working in a ``[0, 360]`` domain shifted by +180."""
    segments: List[Tuple[float, float]] = []
    for start, width in arcs:
        s = start + 180.0
        e = s + width
        if e > 360.0:
            segments.append((s, 360.0))
            segments.append((0.0, e - 360.0))
        else:
            segments.append((s, e))
    segments.sort()

    merged: List[Tuple[float, float]] = []
    for s, e in segments:
        if merged and s <= merged[-1][1] + _EPS:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def _snap(value: float, observed: Sequence[float]) -> float:
    """Round ``value`` to a nearby input longitude, undoing +180/-180 drift."""
    i = bisect.bisect_left(observed, value)
    best = value
    best_err = _SNAP
    for j in (i - 1, i):
        if 0 <= j < len(observed):
            err = abs(observed[j] - value)
            if err <= best_err:
                best_err = err
                best = observed[j]
    return best


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Coordinates are read as EPSG:4326 lon/lat.  The result describes the actual
    extent of the geometry on Earth, so for data crossing the antimeridian
    ``min_lon`` is greater than ``max_lon`` (RFC 7946 section 5.2).  Both
    longitudes are always within ``[-180, 180]``.

    Raises ``ValueError`` if the document contains no positions.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    arcs: List[Tuple[float, float]] = []
    observed: List[float] = []
    min_lat = float("inf")
    max_lat = float("-inf")

    for geometry in _geometries(document):
        for positions in _paths(geometry):
            lons = []
            for position in positions:
                lon = float(position[0])
                lat = float(position[1])
                lons.append(lon)
                observed.append(_wrap180(lon))
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
            if lons:
                arcs.append(_arc(lons))

    if not arcs:
        raise ValueError("GeoJSON document contains no coordinates")

    observed.sort()
    merged = _merge(arcs)

    # Largest gap between merged components; the complement is the answer.
    gap_width = 0.0
    gap_end = merged[0][0]
    for i, (_, end) in enumerate(merged):
        start = merged[(i + 1) % len(merged)][0]
        width = start - end
        if i == len(merged) - 1:
            width += 360.0
        if width > gap_width:
            gap_width = width
            gap_end = start if i != len(merged) - 1 else merged[0][0]

    if gap_width <= _EPS:
        return (-180.0, min_lat, 180.0, max_lat)

    span = 360.0 - gap_width
    min_lon = _snap(_wrap180(gap_end - 180.0), observed)
    max_lon = _snap(_wrap180(min_lon + span), observed)

    return (min_lon, min_lat, max_lon, max_lat)