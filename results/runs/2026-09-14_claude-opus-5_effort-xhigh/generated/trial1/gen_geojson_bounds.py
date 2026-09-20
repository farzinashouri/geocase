"""Geographic bounding boxes for GeoJSON files.

``geojson_bounds(path)`` reads a GeoJSON file whose coordinates are
longitude/latitude degrees in EPSG:4326 (WGS 84) and returns the extent of
every feature in it as ``(min_lon, min_lat, max_lon, max_lat)``.

Antimeridian handling
---------------------
A naive ``min()``/``max()`` over the raw longitudes is wrong for data that
straddles the 180th meridian: a small island at lon 179.9 / -179.9 would come
out as a box spanning the whole planet.  This module instead treats longitude
as an angle on a circle and reports the *shortest* arc that contains all of the
geometry, which is the box that actually describes the data's extent on Earth.

Because the returned longitudes are always kept inside ``[-180, 180]``, a box
that crosses the antimeridian is reported with ``min_lon > max_lon`` -- the
convention of RFC 7946 section 5.2.  Callers that need the numeric width of the
box should compute it as ``(max_lon - min_lon) % 360``.

Connectivity is taken into account: consecutive vertices of a line or a polygon
ring that are more than 180 degrees apart in raw longitude are read as a
segment crossing the antimeridian (the same rule as ``numpy.unwrap``), so files
that have *not* been cut at the antimeridian are handled correctly.  The parts
of a MultiPoint are treated as independent, since they are not connected.

Known limitations: a ring that genuinely has a gap of more than 180 degrees of
longitude between consecutive vertices is ambiguous and is read as the short
way round, and a polygon that encloses a pole is reported using its vertex
latitudes only (its longitude span still comes out as the full circle).
"""

from __future__ import annotations

import json
import os
from typing import Iterable, Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

Position = Tuple[float, float]

# Slack for deciding that an unwrapped path has gone all the way around.
_FULL_CIRCLE_TOL = 1e-9


def geojson_bounds(path: "str | os.PathLike[str]") -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Parameters
    ----------
    path:
        Path to a GeoJSON file containing a FeatureCollection, a Feature, or a
        bare geometry (including GeometryCollection).  Coordinates must be
        longitude/latitude degrees in EPSG:4326.

    Returns
    -------
    tuple of four floats
        The extent of all geometry in the file.  Latitudes are ordered
        ``min_lat <= max_lat``.  Longitudes are always within ``[-180, 180]``;
        ``min_lon > max_lon`` means the box crosses the antimeridian.

    Raises
    ------
    ValueError
        If the document is not recognisable GeoJSON, or contains no
        coordinates at all.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)

    paths = [p for p in _iter_paths(document) if p]
    if not paths:
        raise ValueError(f"no coordinates found in {os.fspath(path)!r}")

    lats = [lat for coords in paths for _, lat in coords]
    min_lat, max_lat = min(lats), max(lats)

    arcs = [_path_arc([lon for lon, _ in coords]) for coords in paths]
    min_lon, max_lon = _merge_arcs(arcs)

    return (min_lon, min_lat, max_lon, max_lat)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def _iter_paths(node: object) -> Iterator[List[Position]]:
    """Yield the coordinate paths of a GeoJSON object.

    A "path" is a sequence of positions whose consecutive members are joined by
    a segment on the ground (a LineString, or one polygon ring).  Standalone
    positions are yielded as single-element paths.
    """
    if not isinstance(node, dict):
        raise ValueError("GeoJSON object expected, got a non-object")

    node_type = node.get("type")

    if node_type == "FeatureCollection":
        for feature in node.get("features") or ():
            yield from _iter_paths(feature)
        return

    if node_type == "Feature":
        geometry = node.get("geometry")
        if geometry is not None:
            yield from _iter_paths(geometry)
        return

    if node_type == "GeometryCollection":
        for geometry in node.get("geometries") or ():
            yield from _iter_paths(geometry)
        return

    coordinates = node.get("coordinates")
    if coordinates is None:
        if node_type is None:
            raise ValueError("GeoJSON object has no 'type' member")
        return

    if node_type == "Point":
        yield [_position(coordinates)]
    elif node_type == "MultiPoint":
        # Separate points are not connected to one another.
        for position in coordinates:
            yield [_position(position)]
    elif node_type == "LineString":
        yield [_position(p) for p in coordinates]
    elif node_type in ("MultiLineString", "Polygon"):
        for part in coordinates:
            yield [_position(p) for p in part]
    elif node_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield [_position(p) for p in ring]
    else:
        raise ValueError(f"unsupported GeoJSON type: {node_type!r}")


def _position(position: Sequence[float]) -> Position:
    """Return ``(lon, lat)`` from a GeoJSON position, dropping any elevation."""
    try:
        lon, lat = float(position[0]), float(position[1])
    except (TypeError, ValueError, IndexError, KeyError) as exc:
        raise ValueError(f"malformed GeoJSON position: {position!r}") from exc
    return (_normalize_lon(lon), lat)


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into ``[-180, 180)``.

    This also accepts input in the 0..360 convention.
    """
    return ((lon + 180.0) % 360.0) - 180.0


# --------------------------------------------------------------------------
# Longitude as an angle on a circle
# --------------------------------------------------------------------------


def _path_arc(lons: Sequence[float]) -> Tuple[float, float]:
    """Return the arc ``(start, length)`` in degrees covered by one path.

    ``start`` is in ``[-180, 180)`` and the arc runs eastward from it.  The
    longitudes are unwrapped first, so a segment that steps by more than 180
    degrees is read as crossing the antimeridian rather than as a jump right
    across the globe.
    """
    unwrapped = [lons[0]]
    offset = 0.0
    for previous, current in zip(lons, lons[1:]):
        delta = current - previous
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        unwrapped.append(current + offset)

    low, high = min(unwrapped), max(unwrapped)
    length = high - low
    if length >= 360.0 - _FULL_CIRCLE_TOL:
        return (-180.0, 360.0)
    return (_normalize_lon(low), length)


def _merge_arcs(arcs: Iterable[Tuple[float, float]]) -> Tuple[float, float]:
    """Return ``(min_lon, max_lon)`` for the shortest arc covering ``arcs``.

    The union of the arcs is taken on the circle; the answer is the complement
    of the widest gap left uncovered.  ``min_lon > max_lon`` if the result
    crosses the antimeridian.
    """
    # Work in [0, 360) so that ordinary interval merging applies, cutting any
    # arc that runs past the seam into two.
    spans: List[Tuple[float, float]] = []
    for start, length in arcs:
        if length >= 360.0 - _FULL_CIRCLE_TOL:
            return (-180.0, 180.0)
        begin = start + 180.0
        end = begin + length
        if end <= 360.0:
            spans.append((begin, end))
        else:
            spans.append((begin, 360.0))
            spans.append((0.0, end - 360.0))

    spans.sort()
    merged: List[Tuple[float, float]] = []
    for begin, end in spans:
        if merged and begin <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((begin, end))

    # The widest uncovered gap, including the one wrapping past the seam.
    count = len(merged)
    widest_gap = -1.0
    gap_index = 0
    for index in range(count):
        gap_start = merged[index][1]
        following = merged[(index + 1) % count][0]
        gap_end = following + 360.0 if index == count - 1 else following
        gap = gap_end - gap_start
        if gap > widest_gap:
            widest_gap = gap
            gap_index = index

    if widest_gap <= 0.0:
        # Every longitude is occupied.
        return (-180.0, 180.0)

    # The box starts where the widest gap ends and ends where that gap starts.
    min_lon = merged[(gap_index + 1) % count][0] - 180.0
    max_lon = merged[gap_index][1] - 180.0
    return (min_lon, max_lon)