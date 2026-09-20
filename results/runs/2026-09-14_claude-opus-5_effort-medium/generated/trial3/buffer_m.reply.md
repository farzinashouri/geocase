```python
"""Accurate metric buffering of WGS84 (EPSG:4326) geometries.

``buffer_m(geom, distance_m)`` buffers a lon/lat geometry by a distance given in
metres and returns the result in lon/lat again.

Method
------
The geometry is projected into an azimuthal-equidistant (AEQD) projection
centred on the geometry itself, buffered there with plain planar Shapely, and
projected back.  AEQD is exact for distances measured from its centre, so the
buffer is accurate anywhere on Earth, including at the poles and across the
antimeridian, as long as the geometry plus the buffer distance stay well away
from the antipode of the centre (enforced below).

Care is taken with the three things that usually go wrong:

* **Edge curvature** - the input is densified before projecting (and the buffer
  is densified before un-projecting), so long edges keep their shape instead of
  being replaced by a single chord in the wrong space.
* **Antimeridian** - output rings are unwrapped into a continuous longitude
  frame and then split at +/-180, so a crossing buffer comes back as a
  MultiPolygon rather than a smeared ring.
* **Poles** - a buffer that encircles a pole is closed along the pole edge
  before splitting, instead of degenerating into a band.

A single ``Point`` is handled exactly, by walking true geodesics outwards from
it with ``pyproj.Geod``.

Importing this module performs no I/O; the PROJ objects are built lazily and
cached on first use.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Geod, Transformer
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform, unary_union

__all__ = ["buffer_m"]

# Beyond this projected radius the AEQD plane folds in on itself near the
# antipode of the projection centre and planar buffering is meaningless.
_MAX_RADIUS_M = 1.9e7

_DEG_PER_M = 1.0 / 111_320.0


@lru_cache(maxsize=1)
def _wgs84() -> CRS:
    return CRS.from_epsg(4326)


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


@lru_cache(maxsize=256)
def _transformers(lat0: float, lon0: float):
    """Forward/inverse transformers for an AEQD projection centred on a point."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0!r} +lon_0={lon0!r} "
        "+x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    )
    fwd = Transformer.from_crs(_wgs84(), aeqd, always_xy=True)
    inv = Transformer.from_crs(aeqd, _wgs84(), always_xy=True)
    return fwd, inv


def _centre(geom: BaseGeometry) -> tuple[float, float]:
    """A representative lon/lat for the geometry, safe across the antimeridian.

    Averaging unit vectors on the sphere avoids the classic "mean of -179 and
    179 is 0" bug and behaves sensibly near the poles.
    """
    coords = shapely.get_coordinates(geom)
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    cos_lat = np.cos(lat)
    vec = np.array(
        [
            np.mean(cos_lat * np.cos(lon)),
            np.mean(cos_lat * np.sin(lon)),
            np.mean(np.sin(lat)),
        ]
    )
    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:  # antipodally balanced input; any centre is as good as another
        return 0.0, 0.0
    x, y, z = vec / norm
    lat0 = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    lon0 = math.degrees(math.atan2(y, x))
    # Round so that nearby calls share a cached transformer (~1 m of centring
    # error, which does not affect AEQD accuracy).
    return round(lat0, 5), round(lon0, 5)


def _unwrap(lons: np.ndarray) -> np.ndarray:
    """Make a sequence of longitudes continuous (no +/-360 jumps between steps)."""
    if lons.size < 2:
        return lons.copy()
    steps = np.diff(lons)
    steps = (steps + 180.0) % 360.0 - 180.0
    return np.concatenate([lons[:1], lons[0] + np.cumsum(steps)])


def _ring_to_polygon(lons: np.ndarray, lats: np.ndarray) -> Polygon:
    """Build a polygon from one ring, closing it over a pole if it encircles one.

    The ring is returned in a *continuous* longitude frame, so its coordinates
    may run outside [-180, 180]; `_split_antimeridian` folds them back.
    """
    lons = _unwrap(lons)
    net = float(lons[-1] - lons[0])
    if abs(net) > 180.0:
        # The ring winds all the way around the globe, i.e. it encloses a pole.
        pole = 90.0 if float(np.mean(lats)) >= 0.0 else -90.0
        lons = np.concatenate([lons, [lons[-1], lons[0]]])
        lats = np.concatenate([lats, [pole, pole]])
    return Polygon(np.column_stack([lons, lats])).buffer(0)


def _split_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Fold a continuous-longitude geometry back into [-180, 180], splitting it."""
    minx, _, maxx, _ = geom.bounds
    k_lo = math.floor((minx + 180.0) / 360.0)
    k_hi = math.floor((maxx + 180.0) / 360.0)
    if k_lo == k_hi == 0:
        return geom
    pieces = []
    for k in range(k_lo, k_hi + 1):
        strip = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        piece = geom.intersection(strip)
        if piece.is_empty:
            continue
        if k:
            piece = shapely_transform(lambda x, y, k=k: (x - 360.0 * k, y), piece)
        pieces.append(piece)
    if not pieces:
        return geom
    return unary_union(pieces) if len(pieces) > 1 else pieces[0]


def _to_wgs84(planar: BaseGeometry, inv: Transformer) -> BaseGeometry:
    """Un-project a planar polygonal geometry and fix poles / antimeridian."""
    polys = (
        list(planar.geoms) if isinstance(planar, MultiPolygon) else [planar]
    )
    out = []
    for poly in polys:
        if poly.is_empty:
            continue
        rings = [poly.exterior, *poly.interiors]
        as_ll = []
        for ring in rings:
            xy = np.asarray(ring.coords)
            lon, lat = inv.transform(xy[:, 0], xy[:, 1])
            as_ll.append(_ring_to_polygon(np.asarray(lon), np.asarray(lat)))
        shell, holes = as_ll[0], as_ll[1:]
        # Subtracting the holes (rather than passing them to Polygon) keeps the
        # result correct when a hole is itself closed over a pole.
        out.append(shell.difference(unary_union(holes)) if holes else shell)
    if not out:
        return Polygon()
    merged = unary_union(out) if len(out) > 1 else out[0]
    return _split_antimeridian(merged)


def _geodesic_circle(point: Point, distance_m: float, n: int) -> BaseGeometry:
    """Exact geodesic disc around a single point."""
    az = np.linspace(-180.0, 180.0, n, endpoint=False)
    lon0 = np.full(n, point.x)
    lat0 = np.full(n, point.y)
    lon, lat, _ = _geod().fwd(lon0, lat0, az, np.full(n, distance_m))
    lon = np.append(lon, lon[0])
    lat = np.append(lat, lat[0])
    return _split_antimeridian(_ring_to_polygon(lon, lat))


def buffer_m(geom: BaseGeometry, distance_m: float, *, quad_segs: int = 64, **buffer_kwargs):
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom : shapely geometry with EPSG:4326 (lon, lat) coordinates.
    distance_m : buffer distance in metres; negative erodes polygons.
    quad_segs : segments per quarter circle used for round joins/caps.
    **buffer_kwargs : forwarded to ``shapely.geometry.BaseGeometry.buffer``
        (``cap_style``, ``join_style``, ``single_sided``, ...).

    Returns
    -------
    A ``Polygon`` or ``MultiPolygon`` in EPSG:4326.  Buffers that cross the
    antimeridian come back split into parts with longitudes in [-180, 180].

    Raises
    ------
    ValueError
        If ``distance_m`` is not finite, or if the geometry plus the buffer
        distance reaches around to the far side of the Earth, where the local
        projection is no longer usable.
    """
    if geom is None:
        return geom

    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be a finite number of metres")
    if geom.is_empty:
        return geom

    # A lone point has an exact answer, so use it.
    if isinstance(geom, Point) and distance_m > 0 and not buffer_kwargs:
        return _geodesic_circle(geom, distance_m, max(4 * quad_segs, 64))

    lat0, lon0 = _centre(geom)
    fwd, inv = _transformers(lat0, lon0)

    # Densify in lon/lat first: the input's edges are straight lines *in this
    # space*, so this is what preserves their shape through the projection.
    step_m = min(max(abs(distance_m) / 4.0, 1000.0), 50_000.0)
    dense = shapely.segmentize(geom, max(step_m * _DEG_PER_M, 1e-5))

    planar = shapely_transform(lambda x, y: fwd.transform(x, y), dense)

    coords = shapely.get_coordinates(planar)
    if not np.isfinite(coords).all():
        raise ValueError("geometry could not be projected; check for invalid lon/lat")
    radius = float(np.max(np.hypot(coords[:, 0], coords[:, 1])))
    if radius + abs(distance_m) > _MAX_RADIUS_M:
        raise ValueError(
            "geometry extent plus buffer distance approaches the antipode of the "
            "geometry; a single local projection cannot represent this buffer"
        )

    buffered = planar.buffer(distance_m, quad_segs=quad_segs, **buffer_kwargs)
    if buffered.is_empty:
        return buffered

    # Keep the outline dense enough that un-projecting traces the true curve.
    buffered = shapely.segmentize(buffered, max(step_m, 1.0))

    return _to_wgs84(buffered, inv)
```