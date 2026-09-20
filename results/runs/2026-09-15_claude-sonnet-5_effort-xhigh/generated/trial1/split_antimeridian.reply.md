```python
"""Utilities for splitting EPSG:4326 polygons that cross the antimeridian."""

from __future__ import annotations

import math

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import split as _shapely_split


def _crosses_antimeridian(coords: list[tuple[float, float]]) -> bool:
    return any(
        abs(lon2 - lon1) > 180.0
        for (lon1, _), (lon2, _) in zip(coords, coords[1:])
    )


def _unwrap_ring(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Remove +-360 longitude jumps so the ring becomes spatially continuous."""
    unwrapped = [(coords[0][0], coords[0][1])]
    offset = 0.0
    prev_lon = coords[0][0]
    for lon, lat in coords[1:]:
        delta = lon - prev_lon
        if delta > 180.0:
            offset -= 360.0
        elif delta < -180.0:
            offset += 360.0
        prev_lon = lon
        unwrapped.append((lon + offset, lat))
    return unwrapped


def _align_to_center(
    coords: list[tuple[float, float]], target_center: float
) -> list[tuple[float, float]]:
    """Shift a ring by a multiple of 360 so it sits near ``target_center``."""
    xs = [x for x, _ in coords]
    center = (min(xs) + max(xs)) / 2.0
    shift = round((target_center - center) / 360.0) * 360.0
    if shift == 0.0:
        return coords
    return [(x + shift, y) for x, y in coords]


def _rewrap_polygon(polygon: Polygon) -> Polygon:
    """Shift a polygon fragment by a multiple of 360 back into [-180, 180]."""
    minx, _, maxx, _ = polygon.bounds
    center = (minx + maxx) / 2.0
    shift = -360.0 * math.floor((center + 180.0) / 360.0)
    if shift == 0.0:
        return polygon

    exterior = [(x + shift, y) for x, y in polygon.exterior.coords]
    interiors = [
        [(x + shift, y) for x, y in ring.coords] for ring in polygon.interiors
    ]
    return Polygon(exterior, interiors)


def split_antimeridian(polygon: Polygon) -> list[Polygon]:
    """Split a longitude/latitude polygon that crosses the antimeridian.

    ``polygon`` is expected to be a shapely ``Polygon`` in EPSG:4326 whose
    longitudes lie in [-180, 180]. If it crosses the antimeridian (i.e.
    consecutive vertices jump between values near +180 and -180), it is cut
    into two or more polygons along that line. Each returned polygon covers
    part of the original region and does not cross the antimeridian (though
    it may touch it at an edge). If the input does not cross the
    antimeridian, it is returned unchanged as a single-element list.
    """
    exterior_coords = list(polygon.exterior.coords)
    interior_coords = [list(ring.coords) for ring in polygon.interiors]

    crosses = _crosses_antimeridian(exterior_coords) or any(
        _crosses_antimeridian(ring) for ring in interior_coords
    )
    if not crosses:
        return [polygon]

    unwrapped_exterior = _unwrap_ring(exterior_coords)
    ext_xs = [x for x, _ in unwrapped_exterior]
    ext_center = (min(ext_xs) + max(ext_xs)) / 2.0

    unwrapped_interiors = [
        _align_to_center(_unwrap_ring(ring), ext_center) for ring in interior_coords
    ]

    unwrapped_polygon = Polygon(unwrapped_exterior, unwrapped_interiors)

    minx, miny, maxx, maxy = unwrapped_polygon.bounds
    lat_min = miny - 1.0
    lat_max = maxy + 1.0

    split_xs = []
    k = math.floor((minx - 180.0) / 360.0) + 1
    while True:
        x = 180.0 + 360.0 * k
        if x >= maxx:
            break
        if x > minx:
            split_xs.append(x)
        k += 1

    geoms: list[Polygon] = [unwrapped_polygon]
    for x in split_xs:
        splitter = LineString([(x, lat_min), (x, lat_max)])
        next_geoms: list[Polygon] = []
        for geom in geoms:
            gminx, _, gmaxx, _ = geom.bounds
            if gminx < x < gmaxx:
                pieces = _shapely_split(geom, splitter)
                next_geoms.extend(pieces.geoms)
            else:
                next_geoms.append(geom)
        geoms = next_geoms

    result: list[Polygon] = []
    for geom in geoms:
        if geom.is_empty:
            continue
        if isinstance(geom, MultiPolygon):
            result.extend(_rewrap_polygon(part) for part in geom.geoms)
        else:
            result.append(_rewrap_polygon(geom))

    return result
```