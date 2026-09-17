"""Buffer EPSG:4326 (lon/lat, WGS84) geometries by a distance in metres.

The geometry is projected into a local azimuthal equidistant projection
centred on the geometry itself, buffered there in metres, and projected
back.  Longitudes are re-wrapped to [-180, 180], geometries that cross the
antimeridian are split, and buffers that swallow a pole are closed along
the +/-90 latitude line so the result is a valid lon/lat polygon.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)


def _center(geom: BaseGeometry) -> tuple[float, float]:
    """Mean position of the vertices on the unit sphere, as (lon, lat) degrees.

    Averaging 3-D unit vectors keeps this correct across the antimeridian
    and at the poles, where averaging raw lon/lat values would not be.
    """
    coords = shapely.get_coordinates(geom)
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    x = (np.cos(lat) * np.cos(lon)).mean()
    y = (np.cos(lat) * np.sin(lon)).mean()
    z = np.sin(lat).mean()
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-12:
        raise ValueError("geometry is spread over more than a hemisphere; cannot pick a projection centre")
    lat0 = math.degrees(math.asin(max(-1.0, min(1.0, z / norm))))
    lon0 = math.degrees(math.atan2(y, x))
    return lon0, lat0


def _apply(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    def _f(c: np.ndarray) -> np.ndarray:
        x, y = transformer.transform(c[:, 0], c[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geom, _f)


def _unwrap(lon: np.ndarray) -> np.ndarray:
    """Make a sequence of longitudes continuous (no jumps larger than 180)."""
    out = np.array(lon, dtype=float, copy=True)
    d = np.diff(out)
    shift = np.where(d > 180.0, -360.0, np.where(d < -180.0, 360.0, 0.0))
    out[1:] += np.cumsum(shift)
    return out


def _wrap_to_180(poly: Polygon) -> BaseGeometry:
    """Cut a polygon with unbounded longitudes into [-180, 180] pieces."""
    minx, _, maxx, _ = poly.bounds
    kmin = math.floor((minx + 180.0) / 360.0)
    kmax = math.floor((maxx + 180.0) / 360.0)
    pieces = []
    for k in range(kmin, kmax + 1):
        window = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        piece = poly.intersection(window)
        if piece.is_empty:
            continue
        piece = unary_union([p for p in shapely.get_parts(piece) if isinstance(p, Polygon)])
        if not piece.is_empty:
            pieces.append(translate(piece, xoff=-360.0 * k))
    return unary_union(pieces) if pieces else Polygon()


def _ring_to_lonlat(ring_xy: np.ndarray, inv: Transformer, north_xy: Optional[tuple[float, float]]) -> BaseGeometry:
    """Convert one projected ring to a valid polygon in lon/lat space."""
    lon, lat = inv.transform(ring_xy[:, 0], ring_xy[:, 1])
    lon = _unwrap(np.asarray(lon, dtype=float))
    lat = np.clip(np.asarray(lat, dtype=float), -90.0, 90.0)

    winding = round((lon[-1] - lon[0]) / 360.0)
    if winding != 0:
        # The ring winds once around the polar axis, so it encloses a pole.
        # Close it along the pole's latitude line so it is a proper cap.
        encloses_north = north_xy is not None and Polygon(ring_xy).contains(shapely.Point(north_xy))
        pole = 90.0 if encloses_north else -90.0
        lon = np.append(lon, [lon[-1], lon[0]])
        lat = np.append(lat, [pole, pole])

    poly = Polygon(np.column_stack([lon, lat]))
    if not poly.is_valid:
        poly = shapely.make_valid(poly)
        poly = unary_union([p for p in shapely.get_parts(poly) if isinstance(p, Polygon)])
        if poly.is_empty:
            return poly
    parts = [_wrap_to_180(p) for p in shapely.get_parts(poly) if isinstance(p, Polygon)]
    return unary_union(parts) if parts else Polygon()


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs) -> BaseGeometry:
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom
        Any shapely geometry with WGS84 longitude/latitude coordinates.
    distance_m
        Buffer distance in metres. Negative values erode polygons.
    **buffer_kwargs
        Passed through to ``shapely.buffer`` (e.g. ``quad_segs``, ``cap_style``).

    Returns
    -------
    shapely geometry in EPSG:4326 with longitudes in [-180, 180]. Buffers
    that cross the antimeridian come back as a MultiPolygon; buffers that
    cover a pole are closed along the +/-90 latitude line.

    Notes
    -----
    Distances are measured in a local azimuthal equidistant projection on
    the WGS84 ellipsoid centred on the input, so the result is accurate for
    inputs that are small compared to the Earth (up to a few thousand km).
    """
    if geom is None or geom.is_empty:
        return geom
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be finite")

    lon0, lat0 = _center(geom)
    local = CRS.from_proj4(f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs")
    fwd = Transformer.from_crs(_WGS84, local, always_xy=True)
    inv = Transformer.from_crs(local, _WGS84, always_xy=True)

    projected = _apply(geom, fwd)
    if not np.isfinite(shapely.get_coordinates(projected)).all():
        raise ValueError("geometry could not be projected; it may span too much of the globe")

    buffered = shapely.buffer(projected, distance_m, **buffer_kwargs)
    if buffered.is_empty:
        return buffered

    nx, ny = fwd.transform(lon0, 90.0)
    north_xy = (nx, ny) if math.isfinite(nx) and math.isfinite(ny) else None

    results = []
    for part in shapely.get_parts(buffered):
        if not isinstance(part, Polygon) or part.is_empty:
            continue
        shell = _ring_to_lonlat(np.asarray(part.exterior.coords), inv, north_xy)
        if shell.is_empty:
            continue
        holes = [_ring_to_lonlat(np.asarray(h.coords), inv, north_xy) for h in part.interiors]
        holes = [h for h in holes if not h.is_empty]
        if holes:
            shell = shell.difference(unary_union(holes))
        if not shell.is_empty:
            results.append(shell)

    if not results:
        return Polygon()
    out = unary_union(results)
    parts = [p for p in shapely.get_parts(out) if isinstance(p, Polygon) and not p.is_empty]
    return unary_union(parts) if parts else Polygon()