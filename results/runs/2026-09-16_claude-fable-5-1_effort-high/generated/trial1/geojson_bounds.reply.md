```python
"""Compute the geographic bounding box of a GeoJSON file.

The input is assumed to be EPSG:4326 (WGS84) with positions given as
``[longitude, latitude, ...]``.  Unlike a naive min/max over raw
coordinates, this implementation handles geometries that cross the
antimeridian (the +/-180 degree meridian) and rings that enclose a pole,
so the returned box describes the real extent of the data on Earth.

Following RFC 7946 section 5.2, a box that crosses the antimeridian is
returned with ``min_lon > max_lon`` (for example ``(170.0, -10.0, -170.0,
10.0)``).  All returned longitudes lie within ``[-180, 180]``.
"""

import json
from typing import Iterable, Iterator, List, Sequence, Tuple

__all__ = ["geojson_bounds"]

_Position = Sequence[float]
_Part = List[_Position]


def _norm_lon(lon: float, upper_inclusive: bool = False) -> float:
    """Wrap a longitude into [-180, 180) or (-180, 180]."""
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    if upper_inclusive and wrapped == -180.0 and lon != -180.0:
        return 180.0
    return wrapped


def _iter_geometries(obj) -> Iterator[dict]:
    """Yield every concrete geometry object contained in a GeoJSON object."""
    if obj is None or not isinstance(obj, dict):
        return
    kind = obj.get("type")
    if kind == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _iter_geometries(feature)
    elif kind == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif kind == "GeometryCollection":
        for geom in obj.get("geometries") or []:
            yield from _iter_geometries(geom)
    elif kind in (
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    ):
        yield obj


def _iter_parts(geom: dict) -> Iterator[Tuple[_Part, bool]]:
    """Yield (coordinate sequence, is_ring) pairs for a single geometry.

    A "part" is a connected path along which longitude is unwrapped.
    Points and MultiPoint members are one-position parts; lines and rings
    are yielded intact.
    """
    kind = geom["type"]
    coords = geom.get("coordinates")
    if coords is None:
        return
    if kind == "Point":
        yield [coords], False
    elif kind == "MultiPoint":
        for pos in coords:
            yield [pos], False
    elif kind == "LineString":
        yield list(coords), False
    elif kind == "MultiLineString":
        for line in coords:
            yield list(line), False
    elif kind == "Polygon":
        for ring in coords:
            yield list(ring), True
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield list(ring), True


def _unwrap_lons(lons: Iterable[float]) -> List[float]:
    """Return longitudes shifted by multiples of 360 so consecutive jumps are <= 180."""
    out: List[float] = []
    for lon in lons:
        if not out:
            out.append(_norm_lon(lon, upper_inclusive=True))
            continue
        prev = out[-1]
        candidate = prev + _norm_lon(lon - prev)
        # _norm_lon returns [-180, 180); prefer +180 over -180 for ties so a
        # segment spanning exactly half the globe keeps its stated direction.
        if candidate == prev - 180.0 and (lon - prev) % 360.0 == 180.0:
            candidate = prev + 180.0
        out.append(candidate)
    return out


def _circular_extent(intervals: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Smallest arc of longitude covering all intervals.

    Each interval is (start, end) in unwrapped degrees with 0 <= end-start < 360.
    Returns (min_lon, max_lon) with both values in [-180, 180]; min_lon may be
    greater than max_lon when the arc crosses the antimeridian.  Returns
    (-180, 180) when the intervals cover the whole circle.
    """
    base: List[List[float]] = []
    for start, end in intervals:
        length = end - start
        s = _norm_lon(start)
        base.append([s, s + length])
    base.sort()

    # Merge in linear space, duplicating everything shifted by +360 so that
    # intervals which wrap past 180 merge with those starting near -180.
    extended = base + [[s + 360.0, e + 360.0] for s, e in base]
    merged: List[List[float]] = []
    for s, e in extended:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    merged = [m for m in merged if -180.0 <= m[0] < 180.0]

    if not merged or any(m[1] - m[0] >= 360.0 for m in merged):
        return -180.0, 180.0

    # The covering arc is the complement of the largest empty gap.
    n = len(merged)
    best_gap = float("-inf")
    best_i = 0
    for i in range(n):
        gap_start = merged[i][1]
        nxt = merged[(i + 1) % n]
        gap_end = nxt[0] if i + 1 < n else nxt[0] + 360.0
        gap = gap_end - gap_start
        if gap > best_gap:
            best_gap = gap
            best_i = i
    if best_gap <= 0.0:
        return -180.0, 180.0

    arc_start = merged[(best_i + 1) % n][0]
    arc_end = merged[best_i][1]
    return _norm_lon(arc_start), _norm_lon(arc_end, upper_inclusive=True)


def geojson_bounds(path) -> Tuple[float, float, float, float]:
    """Return ``(min_lon, min_lat, max_lon, max_lat)`` for a GeoJSON file.

    Coordinates are interpreted as EPSG:4326 longitude/latitude.  Paths and
    rings are unwrapped so that antimeridian crossings are recognised; a box
    that crosses the antimeridian is reported with ``min_lon > max_lon`` as in
    RFC 7946.  Rings that wind fully around the globe are treated as
    enclosing the nearer pole and extend the box to that pole.

    Raises ``ValueError`` if the file contains no coordinates.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    min_lat = float("inf")
    max_lat = float("-inf")
    lon_intervals: List[Tuple[float, float]] = []
    full_circle = False
    saw_coordinate = False

    for geom in _iter_geometries(data):
        for part, is_ring in _iter_parts(geom):
            if not part:
                continue
            lons = [float(p[0]) for p in part]
            lats = [float(p[1]) for p in part]
            saw_coordinate = True

            min_lat = min(min_lat, min(lats))
            max_lat = max(max_lat, max(lats))

            unwrapped = _unwrap_lons(lons)
            lo, hi = min(unwrapped), max(unwrapped)
            net_winding = unwrapped[-1] - unwrapped[0] if len(unwrapped) > 1 else 0.0

            if is_ring and abs(net_winding) >= 180.0:
                # Ring winds around the globe: it encloses a pole.
                full_circle = True
                mean_lat = sum(lats) / len(lats)
                if mean_lat >= 0.0:
                    max_lat = 90.0
                else:
                    min_lat = -90.0
            elif hi - lo >= 360.0:
                full_circle = True
            else:
                lon_intervals.append((lo, hi))

    if not saw_coordinate:
        raise ValueError("GeoJSON file contains no coordinates: %r" % (path,))

    if full_circle:
        min_lon, max_lon = -180.0, 180.0
    else:
        min_lon, max_lon = _circular_extent(lon_intervals)

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```