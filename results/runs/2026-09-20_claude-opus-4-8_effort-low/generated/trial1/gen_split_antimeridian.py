"""Split shapely polygons that cross the antimeridian (EPSG:4326).

Importing this module has no side effects.
"""

from shapely.geometry import Polygon, MultiPolygon, box
from shapely.affinity import translate


def _unwrap_ring(coords):
    """Shift negative longitudes by +360 so a ring straddling the
    antimeridian becomes geometrically continuous around lon=180."""
    return [(lon + 360.0 if lon < 0 else lon, lat) for lon, lat in coords]


def _ring_crosses(coords):
    """A ring crosses the antimeridian if any consecutive vertices jump
    more than 180 degrees in longitude."""
    for (lon0, _), (lon1, _) in zip(coords, coords[1:]):
        if abs(lon1 - lon0) > 180.0:
            return True
    return False


def _polygon_crosses(polygon):
    if _ring_crosses(list(polygon.exterior.coords)):
        return True
    return any(_ring_crosses(list(ring.coords)) for ring in polygon.interiors)


def _explode(geom):
    """Yield the individual, non-empty polygons of a geometry."""
    if geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon):
        for part in geom.geoms:
            if not part.is_empty:
                yield part
    else:  # GeometryCollection or other: keep only polygonal parts
        for part in getattr(geom, "geoms", []):
            yield from _explode(part)


def split_antimeridian(polygon):
    """Split *polygon* (lon/lat, EPSG:4326, lon in [-180, 180]) into a list
    of valid polygons none of which crosses the antimeridian.

    A polygon that does not cross is returned unchanged as a single-element
    list.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("expected a shapely Polygon")

    if not _polygon_crosses(polygon):
        return [polygon]

    # Rebuild the polygon in an unwrapped [0, 360) longitude space so it is
    # geometrically continuous, then clip on the lon=180 meridian.
    shell = _unwrap_ring(list(polygon.exterior.coords))
    holes = [_unwrap_ring(list(r.coords)) for r in polygon.interiors]
    unwrapped = Polygon(shell, holes)
    if not unwrapped.is_valid:
        unwrapped = unwrapped.buffer(0)

    minx, miny, maxx, maxy = unwrapped.bounds

    west_box = box(minx, miny, 180.0, maxy)
    east_box = box(180.0, miny, maxx, maxy)

    result = []
    for part in _explode(unwrapped.intersection(west_box)):
        result.append(part)
    for part in _explode(unwrapped.intersection(east_box)):
        # Shift the eastern part (lon in [180, 360]) back into [-180, 0].
        result.append(translate(part, xoff=-360.0))

    return result