"""Accurate metric buffering of WGS84 (EPSG:4326) geometries.

The public entry point is :func:`buffer_m`, which buffers a lon/lat geometry by
a distance in meters and returns the result back in lon/lat.

Approach
--------
Buffering is a metric operation, so it cannot be done directly in degrees.
Each connected part of the input is reprojected into an azimuthal equidistant
(AEQD) projection centred on that part, buffered there in meters, and projected
back.  AEQD preserves distances measured from its centre exactly (on the WGS84
ellipsoid), so a buffer around a point is a true geodesic circle, and buffers
around small/medium extents are accurate to within the distortion of the part's
own footprint.  Centring per part rather than per geometry keeps that
distortion as small as the input allows.

Wrap-around is handled explicitly: the reprojected outline is unwrapped into a
continuous longitude space, closed over the pole when the buffer covers one,
and then clipped back into the [-180, 180] domain -- so a buffer that crosses
the antimeridian comes back as a multipolygon split at +/-180, and a buffer that
covers a pole comes back as a proper polar cap.

Limitations: a single part whose own extent is continental in scale is still
subject to AEQD distortion away from its centre, and buffering degenerate
(zero-area, self-touching) input inherits shapely's behaviour.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import GeometryCollection, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform, unary_union

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)

# Longest straight segment (meters, in the projected frame) tolerated before an
# edge is densified, and the ceiling on how many vertices densification may add.
_MAX_DENSIFY_VERTICES = 4000


@lru_cache(maxsize=256)
def _transformers(lat_0: float, lon_0: float):
    """Forward/inverse transformers between WGS84 and AEQD at (lat_0, lon_0)."""
    aeqd = CRS.from_dict(
        {
            "proj": "aeqd",
            "lat_0": lat_0,
            "lon_0": lon_0,
            "datum": "WGS84",
            "units": "m",
            "no_defs": True,
        }
    )
    return (
        Transformer.from_crs(_WGS84, aeqd, always_xy=True),
        Transformer.from_crs(aeqd, _WGS84, always_xy=True),
    )


def _apply(transformer, geom: BaseGeometry) -> BaseGeometry:
    return transform(lambda x, y: transformer.transform(x, y), geom)


def _parts(geom: BaseGeometry):
    """Connected components of ``geom``, recursing through collections."""
    if isinstance(geom, (GeometryCollection,)) or geom.geom_type.startswith("Multi"):
        for sub in geom.geoms:
            yield from _parts(sub)
    elif not geom.is_empty:
        yield geom


def _unwrap_input(geom: BaseGeometry) -> BaseGeometry:
    """Shift longitudes so a part straddling the antimeridian stays contiguous."""
    coords = shapely.get_coordinates(geom)
    if len(coords) == 0:
        return geom
    ref = float(coords[0, 0])

    def _shift(x, y):
        x = np.asarray(x, dtype=float)
        return x - 360.0 * np.round((x - ref) / 360.0), y

    return transform(_shift, geom)


def _densify(geom: BaseGeometry, target: float) -> BaseGeometry:
    """Segmentize in the projected frame, without exploding the vertex count."""
    if geom.geom_type in ("Point", "MultiPoint") or target <= 0:
        return geom
    minx, miny, maxx, maxy = geom.bounds
    extent = max(maxx - minx, maxy - miny, 1.0)
    target = max(target, extent / _MAX_DENSIFY_VERTICES)
    return shapely.segmentize(geom, max_segment_length=target)


def _pole_inside(poly: Polygon, fwd, lat: float) -> bool:
    x, y = fwd.transform(0.0, lat)
    if not (np.isfinite(x) and np.isfinite(y)):
        return False
    return poly.covers(Point(x, y))


def _unwrap_ring(ring, lon_0: float) -> np.ndarray:
    """Make a ring's longitudes continuous and rebase them around ``lon_0``."""
    xy = np.asarray(ring.coords, dtype=float)
    lon = np.degrees(np.unwrap(np.radians(xy[:, 0])))
    lon = lon + 360.0 * np.round((lon_0 - lon.mean()) / 360.0)
    return np.column_stack([lon, np.clip(xy[:, 1], -90.0, 90.0)])


def _rebuild(poly_ll: Polygon, fwd, poly_aeqd: Polygon, lon_0: float) -> Polygon:
    """Rebuild an inverse-transformed polygon in continuous longitude space."""
    north = _pole_inside(poly_aeqd, fwd, 90.0)
    south = _pole_inside(poly_aeqd, fwd, -90.0)
    if north and south:
        return box(-180.0, -90.0, 180.0, 90.0)

    shell = _unwrap_ring(poly_ll.exterior, lon_0)
    holes = [_unwrap_ring(h, lon_0) for h in poly_ll.interiors]

    encircles = abs(shell[-1, 0] - shell[0, 0]) > 180.0
    if (north or south) and encircles:
        pole_lat = 90.0 if north else -90.0
        shell = np.vstack(
            [shell, [[shell[-1, 0], pole_lat], [shell[0, 0], pole_lat]]]
        )

    return Polygon(shell, holes)


def _split_at_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Clip a continuous-longitude geometry back into [-180, 180]."""
    minx, _, maxx, _ = geom.bounds
    first = int(np.floor((minx + 180.0) / 360.0))
    last = int(np.floor((maxx + 180.0) / 360.0))
    if first == 0 and last == 0:
        return geom

    pieces = []
    for k in range(first, last + 1):
        window = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        piece = geom.intersection(window)
        if not piece.is_empty:
            pieces.append(translate(piece, xoff=-360.0 * k))
    return unary_union(pieces) if pieces else geom


def _buffer_part(part: BaseGeometry, distance_m: float, quad_segs: int, kwargs):
    part = _unwrap_input(part)
    centre = part.centroid
    lon_0 = float(centre.x)
    lat_0 = float(np.clip(centre.y, -90.0, 90.0))
    fwd, inv = _transformers(round(lat_0, 6), round(lon_0, 6))

    projected = _densify(_apply(fwd, part), abs(distance_m) / 8.0)
    buffered = projected.buffer(distance_m, quad_segs=quad_segs, **kwargs)
    if buffered.is_empty:
        return None

    # Densify the buffer outline too: its straight chords are not straight in
    # lon/lat, so the inverse transform needs vertices to follow the true curve.
    buffered = _densify(buffered, abs(distance_m) / 8.0)

    rebuilt = []
    for poly_aeqd in _parts(buffered):
        if not isinstance(poly_aeqd, Polygon):
            continue
        poly_ll = _apply(inv, poly_aeqd)
        rebuilt.append(_rebuild(poly_ll, fwd, poly_aeqd, lon_0))
    if not rebuilt:
        return None

    merged = shapely.make_valid(unary_union(rebuilt))
    return _split_at_antimeridian(merged)


def buffer_m(geom: BaseGeometry, distance_m: float, *, quad_segs: int = 16, **kwargs):
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` meters.

    Parameters
    ----------
    geom :
        Any shapely geometry with longitude/latitude coordinates in EPSG:4326.
    distance_m :
        Buffer distance in meters.  Negative values erode polygonal input.
    quad_segs :
        Segments per quarter circle used for the rounded parts of the buffer.
    **kwargs :
        Passed through to :meth:`shapely.Geometry.buffer` (``cap_style``,
        ``join_style``, ``mitre_limit``, ``single_sided``).

    Returns
    -------
    shapely geometry in EPSG:4326.  A buffer crossing the antimeridian is
    returned split at +/-180; a buffer covering a pole is returned as a polar
    cap reaching latitude +/-90.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom)!r}")
    distance_m = float(distance_m)
    if not np.isfinite(distance_m):
        raise ValueError("distance_m must be finite")
    if geom.is_empty:
        return geom

    results = [
        result
        for part in _parts(geom)
        if (result := _buffer_part(part, distance_m, quad_segs, kwargs)) is not None
    ]
    if not results:
        return Polygon()
    return shapely.make_valid(unary_union(results))