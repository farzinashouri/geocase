Note: file writes and command execution were declined in this session, so the module below is verified by hand-tracing (simple polygon, antimeridian line, Fiji-style split MultiPolygon, the RFC 7946 split-MultiLineString example, a whole-world rectangle, and out-of-range longitudes) rather than by running it. The key convention is that an extent crossing the antimeridian is returned with `min_lon > max_lon`, per RFC 7946 §5.2 — that is the only way to give the true (narrow) extent while keeping longitudes in `[-180, 180]`.

```python
"""Bounding boxes for GeoJSON files whose coordinates are WGS84 (EPSG:4326).

Longitude is periodic, so the obvious ``min()``/``max()`` over every coordinate
in a file describes the wrong side of the planet as soon as the data straddles
the antimeridian: two islands at 179 and -179 lie two degrees apart, not 358.
This module reports the narrowest box that still contains every vertex.

Following RFC 7946 section 5.2, a box that crosses the antimeridian comes back
with ``min_lon > max_lon`` and is read as starting at ``min_lon`` and running
*eastward* to ``max_lon``.  That convention is what keeps every returned
longitude inside [-180, 180] instead of leaking values such as 181.

Two assumptions are baked in, both of them ordinary GIS practice:

* consecutive vertices of a line or ring are joined by the shorter of the two
  ways round, so one edge never spans more than 180 degrees of longitude;
* disjoint parts -- separate features, multi-geometries, rings -- are covered
  by the narrowest arc containing all of them, with exact ties resolved in
  favour of the conventional non-crossing box.

The only public name is :func:`geojson_bounds`.  Importing has no side effects.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Iterator

__all__ = ["geojson_bounds"]

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


def geojson_bounds(path: str | os.PathLike[str]) -> tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    The file may hold a ``FeatureCollection``, a ``Feature``, a
    ``GeometryCollection`` or a bare geometry; every vertex reachable from it is
    bounded, and ``null`` geometries are skipped.  Any ``bbox`` member already in
    the file is ignored in favour of the coordinates themselves.

    All four values are degrees in EPSG:4326, with longitudes in [-180, 180].
    ``min_lon > max_lon`` means the extent crosses the antimeridian and runs east
    from ``min_lon``, over 180, to ``max_lon`` (RFC 7946 section 5.2).

    Raises ``ValueError`` if the document is not usable GeoJSON or holds no
    coordinates at all.
    """
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)

    min_lat = math.inf
    max_lat = -math.inf
    arcs: list[tuple[float, float, bool]] = []
    for geometry in _iter_geometries(document):
        for run in _coordinate_runs(geometry):
            positions = [_position(raw) for raw in run]
            if not positions:
                continue
            for _, lat in positions:
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
            arcs.append(_longitude_arc(positions))

    if not arcs:
        raise ValueError(f"no coordinates to bound in {os.fspath(path)!r}")

    min_lon, max_lon = _longitude_extent(arcs)
    return (min_lon, min_lat, max_lon, max_lat)


def _iter_geometries(node: object) -> Iterator[dict]:
    """Yield every geometry object reachable from a GeoJSON node."""
    if not isinstance(node, dict):
        raise ValueError(f"expected a GeoJSON object, got {type(node).__name__}")

    node_type = node.get("type")
    if node_type == "FeatureCollection":
        for feature in node.get("features") or ():
            yield from _iter_geometries(feature)
    elif node_type == "Feature":
        geometry = node.get("geometry")
        if geometry is not None:  # a null geometry is legal, and empty
            yield from _iter_geometries(geometry)
    elif node_type == "GeometryCollection":
        for geometry in node.get("geometries") or ():
            yield from _iter_geometries(geometry)
    elif node_type in _GEOMETRY_TYPES:
        yield node
    else:
        raise ValueError(f"unsupported GeoJSON type: {node_type!r}")


def _coordinate_runs(geometry: dict) -> Iterator[list]:
    """Yield a geometry's connected vertex runs.

    Consecutive members of a run are joined by an edge, which is what lets the
    antimeridian logic tell a real crossing from an unrelated neighbour.
    Isolated points come back as one-element runs.
    """
    geometry_type = geometry["type"]
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list):
        raise ValueError(f"{geometry_type} geometry has no usable 'coordinates'")

    if geometry_type == "Point":
        yield [coordinates]
    elif geometry_type == "MultiPoint":
        for position in coordinates:
            yield [position]
    elif geometry_type == "LineString":
        yield coordinates
    elif geometry_type in ("MultiLineString", "Polygon"):
        yield from coordinates
    else:  # MultiPolygon
        for polygon in coordinates:
            yield from polygon


def _position(raw: object) -> tuple[float, float]:
    """Read ``(lon, lat)`` from a GeoJSON position, ignoring any elevation."""
    try:
        lon = float(raw[0])  # type: ignore[index]
        lat = float(raw[1])  # type: ignore[index]
    except (IndexError, KeyError, TypeError, ValueError):
        raise ValueError(f"malformed GeoJSON position: {raw!r}") from None
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(f"non-finite GeoJSON position: {raw!r}")
    return lon, lat


def _wrap180(degrees: float) -> float:
    """Fold *degrees* onto [-180, 180], leaving in-range values untouched.

    Used for longitudes and for the east-west step between two of them; for a
    step this picks the shorter way round, and an exactly antipodal step keeps
    whichever sign the file wrote it with.
    """
    if -180.0 <= degrees <= 180.0:
        return degrees
    return degrees - 360.0 * math.floor((degrees + 180.0) / 360.0)


def _longitude_arc(positions: list[tuple[float, float]]) -> tuple[float, float, bool]:
    """Reduce one connected run to ``(west, east, full)``.

    The arc starts at ``west`` and runs *east* to ``east``; ``full`` marks a run
    that wraps the globe outright.  Walking the run and accumulating shortest
    steps is what unwraps an antimeridian crossing: the running total leaves
    [-180, 180], while ``west`` and ``east`` stay the untouched longitudes of the
    vertices that reach the extremes.
    """
    west = east = previous = _wrap180(positions[0][0])
    track = lowest = highest = west
    both_spellings = False  # the +/-180 meridian written as both -180 and 180

    for lon, _ in positions[1:]:
        canonical = _wrap180(lon)
        if abs(canonical - previous) == 360.0:
            both_spellings = True
        track += _wrap180(canonical - track)  # never step more than 180 degrees
        if track < lowest:
            lowest, west = track, canonical
        elif track > highest:
            highest, east = track, canonical
        previous = canonical

    width = highest - lowest
    # A run pinned to the +/-180 meridian yet written with both spellings -- the
    # usual whole-world rectangle -- swept the globe rather than standing still.
    full = width >= 360.0 or (width == 0.0 and both_spellings)
    return west, east, full


def _longitude_extent(arcs: list[tuple[float, float, bool]]) -> tuple[float, float]:
    """Cover every arc with the narrowest one, as ``(min_lon, max_lon)``."""
    spans: list[list[float]] = []
    for west, east, full in arcs:
        if full:
            return -180.0, 180.0
        if east >= west:
            spans.append([west, east])
        else:  # runs east over the antimeridian, so it lands in both halves
            spans.append([west, 180.0])
            spans.append([-180.0, east])

    spans.sort()
    merged: list[list[float]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])

    # The answer is the complement of the widest *uncovered* arc.  The gap
    # straddling the antimeridian is the first candidate tried, so an exact tie
    # keeps the conventional west-to-east box.
    widest = merged[0][0] + 360.0 - merged[-1][1]
    after_gap = 0
    for index in range(1, len(merged)):
        gap = merged[index][0] - merged[index - 1][1]
        if gap > widest:
            widest, after_gap = gap, index

    if widest <= 0.0:  # every meridian is covered
        return -180.0, 180.0
    return merged[after_gap][0], merged[after_gap - 1][1]
```