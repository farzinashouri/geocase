"""Geographic bounding boxes for GeoJSON files in EPSG:4326 (WGS84).

``geojson_bounds(path)`` returns ``(min_lon, min_lat, max_lon, max_lat)`` as
plain floats describing the real extent of the geometry on the globe.

Longitudes are always inside ``[-180, 180]``.  Because longitude is cyclic, the
extent of a feature that crosses the antimeridian cannot be written as an
interval with ``min_lon <= max_lon`` without inflating it to most of the planet.
Following RFC 7946 section 5.2, such a box is reported with ``min_lon >
max_lon``: the box is the arc that runs east from ``min_lon``, over +/-180, to
``max_lon``.

Only the standard library is used.  Importing this module has no side effects.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

_EPS = 1e-9
_FULL = 360.0

_SIMPLE_TYPES = frozenset(
    {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }
)


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` is anything ``open()`` accepts.  The document may be a
    FeatureCollection, a Feature, a GeometryCollection or a bare geometry.

    Raises ``ValueError`` if the document holds no coordinates or contains a
    member this module does not understand.
    """
    with open(path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    return _bounds_of(doc)


# --------------------------------------------------------------------------- #
# traversal
# --------------------------------------------------------------------------- #


def _iter_geometries(obj: Any) -> Iterator[Dict[str, Any]]:
    """Yield every simple (non-collection) geometry in a GeoJSON object."""
    if not isinstance(obj, dict):
        raise ValueError("expected a GeoJSON object, got %r" % type(obj).__name__)

    gtype = obj.get("type")
    if gtype == "FeatureCollection":
        for feature in obj.get("features") or ():
            yield from _iter_geometries(feature)
    elif gtype == "Feature":
        geometry = obj.get("geometry")
        if geometry is not None:  # a null geometry is legal and contributes nothing
            yield from _iter_geometries(geometry)
    elif gtype == "GeometryCollection":
        for geometry in obj.get("geometries") or ():
            yield from _iter_geometries(geometry)
    elif gtype in _SIMPLE_TYPES:
        yield obj
    else:
        raise ValueError("unsupported GeoJSON type: %r" % (gtype,))


def _parts(geom: Dict[str, Any]) -> Iterator[Tuple[Sequence[Sequence[float]], bool]]:
    """Yield ``(positions, closed)`` for each connected run of vertices.

    Consecutive positions within a run are joined by an edge, which is what lets
    us tell "this line hops the antimeridian" from "these two points sit on
    opposite sides of the world".  Separate parts of a multi-geometry are
    therefore yielded separately, as is each point of a MultiPoint.
    """
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if coords is None:
        return

    if gtype == "Point":
        yield (coords,), False
    elif gtype == "MultiPoint":
        for position in coords:
            yield (position,), False
    elif gtype == "LineString":
        yield coords, False
    elif gtype == "MultiLineString":
        for line in coords:
            yield line, False
    elif gtype == "Polygon":
        for ring in coords:
            yield ring, True
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield ring, True
    else:  # pragma: no cover - _iter_geometries already filtered these out
        raise ValueError("unsupported geometry type: %r" % (gtype,))


# --------------------------------------------------------------------------- #
# longitude helpers
# --------------------------------------------------------------------------- #


def _normalize(lon: float) -> float:
    """Fold a longitude into ``[-180, 180)``."""
    return ((lon + 180.0) % _FULL) - 180.0


def _short_delta(delta: float) -> float:
    """The signed longitude step of the shorter of the two ways round."""
    return ((delta + 180.0) % _FULL) - 180.0


def _unwrap(lons: List[float]) -> List[float]:
    """Make longitudes continuous by assuming each edge takes the short way.

    The result may leave ``[-180, 180]``; that is the point.  A line running
    179 -> -179 unwraps to 179 -> 181, so its span is 2 degrees rather than 358.
    """
    out = [lons[0]]
    for lon in lons[1:]:
        out.append(out[-1] + _short_delta(lon - out[-1]))
    return out


def _covering_arc(arcs: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Smallest arc of the longitude circle containing every input arc.

    ``arcs`` are ``(start, width)`` pairs with ``0 <= width < 360``.  The arcs
    are merged into a union, and the answer is the complement of the union's
    widest gap.
    """
    segments: List[Tuple[float, float]] = []
    for start, width in arcs:
        begin = _normalize(start)
        end = begin + width
        if end > 180.0 + _EPS:
            # Straddles the antimeridian: cut it in two so we can work linearly.
            segments.append((begin, 180.0))
            segments.append((-180.0, end - _FULL))
        else:
            segments.append((begin, min(end, 180.0)))

    segments.sort()
    merged: List[List[float]] = []
    for begin, end in segments:
        if merged and begin <= merged[-1][1] + _EPS:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([begin, end])

    count = len(merged)
    gaps = []
    for i in range(count):
        j = (i + 1) % count
        gap = merged[j][0] - merged[i][1]
        if j == 0:  # the gap that wraps across the antimeridian
            gap += _FULL
        gaps.append(gap)

    widest = max(gaps)
    if widest <= _EPS:
        return -180.0, 180.0

    # Ties go to the wrapping gap, which keeps ordinary geometry non-crossing.
    index = count - 1 if gaps[count - 1] >= widest - _EPS else gaps.index(widest)
    min_lon = merged[(index + 1) % count][0]
    max_lon = merged[index][1]

    # A vertex exactly on the antimeridian normalizes to -180, which can make a
    # box look like it crosses when it merely touches.  Prefer +180 there.
    if min_lon > max_lon and abs(max_lon + 180.0) <= _EPS:
        max_lon = 180.0

    return min_lon, max_lon


# --------------------------------------------------------------------------- #
# the computation
# --------------------------------------------------------------------------- #


def _bounds_of(doc: Any) -> Tuple[float, float, float, float]:
    min_lat = math.inf
    max_lat = -math.inf
    arcs: List[Tuple[float, float]] = []
    all_longitudes = False
    holds_north_pole = False
    holds_south_pole = False
    saw_position = False

    for geom in _iter_geometries(doc):
        for positions, closed in _parts(geom):
            lons: List[float] = []
            for position in positions:
                if len(position) < 2:
                    raise ValueError("a position needs at least two numbers")
                lon = float(position[0])
                lat = float(position[1])
                if not (math.isfinite(lon) and math.isfinite(lat)):
                    raise ValueError("non-finite coordinate in GeoJSON")
                lons.append(_normalize(lon))
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
                saw_position = True

            if not lons:
                continue

            unwrapped = _unwrap(lons)

            if closed:
                # Total longitude turned by the ring, closing edge included.  A
                # full turn means the ring encircles a pole; travelling east
                # keeps the interior on the left, i.e. to the north.
                winding = (unwrapped[-1] - unwrapped[0]) + _short_delta(
                    lons[0] - unwrapped[-1]
                )
                if abs(winding) > 180.0:
                    all_longitudes = True
                    if winding > 0.0:
                        holds_north_pole = True
                    else:
                        holds_south_pole = True

            span = max(unwrapped) - min(unwrapped)
            if span >= _FULL - _EPS:
                all_longitudes = True
            else:
                arcs.append((min(unwrapped), span))

    if not saw_position:
        raise ValueError("GeoJSON contains no coordinates")

    if holds_north_pole:
        max_lat = 90.0
    if holds_south_pole:
        min_lat = -90.0

    if all_longitudes or not arcs:
        min_lon, max_lon = -180.0, 180.0
    else:
        min_lon, max_lon = _covering_arc(arcs)

    return float(min_lon), float(min_lat), float(max_lon), float(max_lat)