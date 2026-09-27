"""Convert shapely geometries to RFC 7946 GeoJSON geometry objects.

RFC 7946 mandates that coordinates use the WGS 84 datum with longitude,
latitude ordering (CRS "OGC:CRS84", equivalent to EPSG:4326). This module
reprojects the input geometry from its source EPSG code to WGS 84 and emits a
plain ``dict`` conforming to the geometry-object rules of the spec, including
the right-hand rule for polygon ring winding.
"""

from pyproj import CRS, Transformer
from shapely.geometry import mapping
from shapely.ops import transform

__all__ = ["to_rfc7946"]


def _round_coords(obj):
    """Recursively coerce coordinate numbers to plain floats.

    Turns any numpy scalars produced during transformation into native
    Python floats and rebuilds tuples as lists (JSON arrays).
    """
    if isinstance(obj, (list, tuple)):
        return [_round_coords(v) for v in obj]
    return float(obj)


def _ring_is_ccw(ring):
    """Return True if a linear ring (list of [x, y, ...]) is counter-clockwise.

    Uses the signed-area (shoelace) test on the planar lon/lat values.
    """
    area = 0.0
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        area += (x1 * y2) - (x2 * y1)
    return area > 0.0


def _wind_polygon(rings):
    """Apply the RFC 7946 right-hand rule to one polygon's rings.

    Exterior ring counter-clockwise, interior rings (holes) clockwise.
    """
    if not rings:
        return rings
    fixed = []
    for i, ring in enumerate(rings):
        ccw = _ring_is_ccw(ring)
        want_ccw = (i == 0)  # exterior wants CCW, holes want CW
        fixed.append(ring if ccw == want_ccw else list(reversed(ring)))
    return fixed


def _fix_winding(geometry):
    """Recursively enforce polygon winding order on a GeoJSON geometry dict."""
    gtype = geometry["type"]
    if gtype == "Polygon":
        geometry["coordinates"] = _wind_polygon(geometry["coordinates"])
    elif gtype == "MultiPolygon":
        geometry["coordinates"] = [
            _wind_polygon(poly) for poly in geometry["coordinates"]
        ]
    elif gtype == "GeometryCollection":
        for g in geometry["geometries"]:
            _fix_winding(g)
    return geometry


def to_rfc7946(geom, epsg):
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object (a ``dict``).

    Parameters
    ----------
    geom : shapely geometry
        The geometry whose coordinates are expressed in the CRS given by
        ``epsg``.
    epsg : int
        The EPSG code of ``geom``'s coordinate reference system.

    The returned dict has only ``type`` and ``coordinates`` members (or
    ``geometries`` for a GeometryCollection), with coordinates reprojected to
    WGS 84 in longitude, latitude order.
    """
    src = CRS.from_epsg(int(epsg))
    dst = CRS.from_epsg(4326)

    if src != dst:
        # always_xy keeps input/output in (lon/x, lat/y) ordering so the
        # emitted GeoJSON uses the RFC-mandated longitude, latitude order.
        transformer = Transformer.from_crs(src, dst, always_xy=True)
        geom = transform(transformer.transform, geom)

    geometry = mapping(geom)
    geometry = _normalize(geometry)
    return _fix_winding(geometry)


def _normalize(geometry):
    """Return a clean geometry dict with float coordinates and only the
    RFC 7946 members."""
    gtype = geometry["type"]
    if gtype == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_normalize(g) for g in geometry["geometries"]],
        }
    return {
        "type": gtype,
        "coordinates": _round_coords(geometry["coordinates"]),
    }