```python
"""Bounding box of a GeoJSON (EPSG:4326) file, with antimeridian awareness.

The public entry point is :func:`geojson_bounds`.  It returns
``(min_lon, min_lat, max_lon, max_lat)`` in the RFC 7946 ``bbox`` order
(west, south, east, north), where:

* every longitude is reported inside ``[-180, 180]``;
* input longitudes outside that range (e.g. ``190``) are wrapped onto it;
* line and ring segments that span more than 180 degrees as written are
  taken to go the short way round, i.e. across the antimeridian;
* geometry that touches or crosses the antimeridian is reported the way
  RFC 7946 section 5.2 prescribes, with ``min_lon > max_lon``
  (e.g. Fiji -> ``(177.0, -20.0, -178.0, -16.0)``);
* geometry whose longitude coverage wraps the whole globe is reported as
  ``(-180.0, ..., 180.0, ...)``.

Only the standard library is used.  Importing this module has no side effects.
"""

import json
import math

__all__ = ["geojson_bounds"]

_FULL = 360.0
_HALF = 180.0

# Nesting depth of a geometry's ``coordinates`` member below the level of a
# single list of positions (0 == the member is itself one position).
_DEPTH = {
    "Point": 0,
    "MultiPoint": 1,
    "LineString": 1,
    "MultiLineString": 2,
    "Polygon": 2,
    "MultiPolygon": 3,
}
_UNCONNECTED = frozenset(("Point", "MultiPoint"))


def _norm_lon(lon):
    """Map a longitude onto the half-open range [-180, 180)."""
    return ((lon + _HALF) % _FULL) - _HALF


def _iter_geometries(obj):
    """Yield ``(type, coordinates)`` for every concrete geometry in ``obj``."""
    if obj is None:
        return
    if not isinstance(obj, dict):
        raise ValueError("GeoJSON object must be a JSON object")
    gtype = obj.get("type")
    if gtype == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _iter_geometries(feature)
    elif gtype == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif gtype == "GeometryCollection":
        for geometry in obj.get("geometries") or []:
            yield from _iter_geometries(geometry)
    elif gtype in _DEPTH:
        yield gtype, obj.get("coordinates")
    else:
        raise ValueError("unsupported GeoJSON type: %r" % (gtype,))


def _position_lists(coords, depth):
    """Yield each list of positions (a point list, line or ring) in ``coords``."""
    if depth == 0:
        yield [coords]
    elif depth == 1:
        yield coords
    else:
        for part in coords:
            yield from _position_lists(part, depth - 1)


def _segment_arc(a, b):
    """Longitude arc covered by the segment a -> b as ``(start, width)``.

    ``start`` is normalised to [-180, 180).  Segments written wider than
    180 degrees are assumed to go the short way round (across the
    antimeridian); segments 360 degrees or wider cover the whole circle.
    """
    delta = b - a
    if abs(delta) >= _FULL:
        return -_HALF, _FULL
    if delta > _HALF:
        delta -= _FULL
    elif delta < -_HALF:
        delta += _FULL
    if delta >= 0:
        return _norm_lon(a), delta
    return _norm_lon(b), -delta


def _add_arc(intervals, start, width):
    """Store the arc [start, start + width], split at the antimeridian."""
    end = start + width
    if end > _HALF:
        intervals.append((start, _HALF))
        intervals.append((-_HALF, end - _FULL))
    else:
        intervals.append((start, end))


def _lon_range(intervals, wrapped):
    """Reduce the collected arcs to ``(west, east)``.

    ``wrapped`` says whether any raw longitude lay outside [-180, 180]; it is
    treated, together with geometry that touches the antimeridian, as evidence
    that an antimeridian-crossing box is the honest description.
    """
    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])

    first_start = merged[0][0]
    last_end = merged[-1][1]
    # Uncovered arc that contains the antimeridian.
    wrap_gap = (first_start + _HALF) + (_HALF - last_end)

    # Largest uncovered arc that does not contain the antimeridian.
    best_gap = -1.0
    best_i = None
    for i in range(len(merged) - 1):
        gap = merged[i + 1][0] - merged[i][1]
        if gap > best_gap:
            best_gap, best_i = gap, i

    crossing_evidence = wrap_gap <= 0.0 or wrapped
    if not crossing_evidence or best_i is None or best_gap <= wrap_gap:
        # Plain west..east box (also yields (-180, 180) for full coverage).
        return first_start, last_end

    west = merged[best_i + 1][0]
    east = merged[best_i][1]
    if east == -_HALF:
        east = _HALF
    return west, east


def geojson_bounds(path):
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    ``path`` names a file holding a FeatureCollection, a Feature or a bare
    geometry whose positions are EPSG:4326 longitude/latitude.  Longitudes in
    the result lie within [-180, 180].  If the geometry crosses the
    antimeridian the box is given RFC 7946 style with ``min_lon > max_lon``.

    Raises ``ValueError`` if the file contains no coordinates.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)

    min_lat = math.inf
    max_lat = -math.inf
    intervals = []
    wrapped = False
    full = False
    count = 0

    for gtype, coords in _iter_geometries(data):
        if not coords:
            continue
        connected = gtype not in _UNCONNECTED
        for positions in _position_lists(coords, _DEPTH[gtype]):
            prev_lon = None
            for pos in positions:
                if len(pos) < 2:
                    continue
                lon = float(pos[0])
                lat = float(pos[1])
                count += 1
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
                if lon < -_HALF or lon > _HALF:
                    wrapped = True
                if connected and prev_lon is not None:
                    start, width = _segment_arc(prev_lon, lon)
                    if width >= _FULL:
                        full = True
                    else:
                        _add_arc(intervals, start, width)
                else:
                    _add_arc(intervals, _norm_lon(lon), 0.0)
                prev_lon = lon

    if count == 0:
        raise ValueError("GeoJSON file contains no coordinates: %r" % (path,))

    if full:
        return (-_HALF, min_lat, _HALF, max_lat)

    west, east = _lon_range(intervals, wrapped)
    return (float(west), float(min_lat), float(east), float(max_lat))
```