Key detail: a naive `min`/`max` over coordinates returns a near-global box for anything touching the antimeridian, so longitudes are handled as arcs on a circle (wrapping boxes come back with `min_lon > max_lon`, per RFC 7946 §5.2, keeping every value in `[-180, 180]`). Sandbox permissions blocked my attempts to write and execute a scratch test file, so the behaviour below is hand-traced, not run.

```python
"""Bounding boxes for GeoJSON files whose coordinates are WGS84 (EPSG:4326).

Importing this module has no side effects; it only needs ``json`` and ``os``
from the standard library.

The subtle part is longitude.  Taking ``min``/``max`` over every coordinate
reports a near-global box for anything that straddles the antimeridian: a
small island group at 179E..179W comes back as 179W..179E, 358 degrees wide
and pointing the wrong way round the Earth.  Longitudes are therefore treated
as arcs on a circle.  Each connected component (a ring, a line, a point) is
"unwrapped" so consecutive vertices never jump more than 180 degrees, the
resulting arcs are merged, and the box is the complement of the widest empty
wedge.  When that box straddles the antimeridian the result has
``min_lon > max_lon`` -- the convention of RFC 7946 section 5.2 -- which keeps
every returned longitude inside [-180, 180].
"""

from __future__ import annotations

import json
import os
from typing import Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

_TURN = 360.0

Position = Sequence[float]


def geojson_bounds(path: "str | os.PathLike[str]") -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` may point at any GeoJSON object: a FeatureCollection, a Feature,
    a bare geometry or a GeometryCollection.  Any ``bbox`` members in the file
    are ignored; the extent is computed from the coordinates themselves.

    The box describes the real extent of the geometry on Earth, so data that
    crosses the antimeridian yields a wrapping box with ``min_lon > max_lon``
    (e.g. ``(177.0, -18.0, -178.0, -16.0)`` for Fiji) instead of one stretched
    the long way around the globe.  Where features are disjoint the narrowest
    box that covers them all is returned.

    Raises ``ValueError`` if the document holds no coordinates.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    lats: List[float] = []
    arcs: List[List[float]] = []
    for component in _components(document):
        lons: List[float] = []
        for position in component:
            lons.append(float(position[0]))
            lats.append(float(position[1]))
        if lons:
            arcs.append(_arc(lons))

    if not arcs:
        raise ValueError("no coordinates found in " + repr(os.fspath(path)))

    min_lon, max_lon = _longitude_extent(arcs)
    return (min_lon, min(lats), max_lon, max(lats))


def _components(node: object) -> Iterator[Sequence[Position]]:
    """Yield each connected run of positions in a GeoJSON object.

    Rings and lines are yielded whole so they can be unwrapped as a unit; the
    members of a MultiPoint are yielded one at a time because they are not
    connected to each other.
    """
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    coordinates = node.get("coordinates")

    if kind == "FeatureCollection":
        for feature in node.get("features") or ():
            yield from _components(feature)
    elif kind == "Feature":
        yield from _components(node.get("geometry"))
    elif kind == "GeometryCollection":
        for geometry in node.get("geometries") or ():
            yield from _components(geometry)
    elif kind == "Point":
        if coordinates:
            yield [coordinates]
    elif kind == "MultiPoint":
        for position in coordinates or ():
            if position:
                yield [position]
    elif kind == "LineString":
        if coordinates:
            yield coordinates
    elif kind in ("MultiLineString", "Polygon"):
        for part in coordinates or ():
            if part:
                yield part
    elif kind == "MultiPolygon":
        for polygon in coordinates or ():
            for ring in polygon or ():
                if ring:
                    yield ring


def _arc(lons: Sequence[float]) -> List[float]:
    """Collapse one component's longitudes into an arc ``[start, start + width]``.

    Consecutive vertices are taken to follow the shorter way round, so a ring
    stepping 179 -> -179 reads as a two degree hop over the antimeridian rather
    than a 358 degree sweep back across the Pacific.  ``start`` lands in
    [-180, 180); the end may run past 180.
    """
    unwrapped = [lons[0]]
    for lon in lons[1:]:
        previous = unwrapped[-1]
        step = lon - previous
        step -= _TURN * round(step / _TURN)
        unwrapped.append(previous + step)

    low = min(unwrapped)
    width = min(max(unwrapped) - low, _TURN)
    start = _wrap(low)
    return [start, start + width]


def _longitude_extent(arcs: List[List[float]]) -> Tuple[float, float]:
    """Merge longitude arcs and return the complement of the widest gap."""
    merged: List[List[float]] = []
    for start, end in sorted(arcs):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # An arc running past +180 can also cover the arcs at the head of the list,
    # which is how the two halves of an antimeridian-split polygon rejoin.
    while len(merged) > 1 and merged[-1][1] >= merged[0][0] + _TURN:
        first = merged.pop(0)
        merged[-1][1] = max(merged[-1][1], first[1] + _TURN)

    if merged[-1][1] - merged[0][0] >= _TURN:
        return (-180.0, 180.0)

    # Gap i runs from the end of arc i to the start of the next one, the last
    # gap wrapping from the final arc back round to the first.  On a tie the
    # wrapping gap wins, which yields the plain non-wrapping box.
    gaps = [(merged[i + 1][0] - merged[i][1], i) for i in range(len(merged) - 1)]
    gaps.append((merged[0][0] + _TURN - merged[-1][1], len(merged) - 1))
    _, widest = max(gaps)

    min_lon = merged[(widest + 1) % len(merged)][0]
    max_lon = merged[widest][1]
    return (min_lon, _wrap_end(max_lon))


def _wrap(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % _TURN - 180.0


def _wrap_end(lon: float) -> float:
    """Wrap the eastern edge of a box into [-180, 180], preferring +180."""
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = _wrap(lon)
    return 180.0 if wrapped == -180.0 else wrapped
```