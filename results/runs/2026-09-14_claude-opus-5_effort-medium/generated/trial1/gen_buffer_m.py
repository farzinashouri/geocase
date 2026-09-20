"""Geodesically accurate metric buffering of EPSG:4326 (lon/lat) geometries.

The standard trick of ``geom.buffer(d / 111320)`` is only correct near the
equator, and buffering in a fixed projection (Web Mercator, a single UTM zone)
degrades away from that projection's zone of validity.  Instead, every call here
builds a *local* azimuthal equidistant (AEQD) projection centred on the input
geometry, buffers there -- where distances from the centre are true metres --
and converts the result back to lon/lat.

The back-conversion is antimeridian-aware: buffers that cross +/-180 deg come
back as a MultiPolygon split at the dateline, and buffers that enclose a pole
are closed along the corresponding +/-90 deg edge instead of collapsing into a
sliver.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import LinearRing, MultiPolygon, Polygon, box
from shapely.ops import unary_union

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)

# Mean Earth radius (metres), used only for rough magnitude checks.
_R_EARTH = 6_371_008.8

# AEQD becomes singular at the antipode of its origin; refuse to go near it.
_MAX_RADIUS_M = 0.85 * math.pi * _R_EARTH


@lru_cache(maxsize=256)
def _transformers(lon0: float, lat0: float):
    """Forward/inverse transformers between WGS84 and a local AEQD at (lon0, lat0)."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        f"+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    )
    fwd = Transformer.from_crs(_WGS84, aeqd, always_xy=True)
    inv = Transformer.from_crs(aeqd, _WGS84, always_xy=True)
    return fwd, inv


def _center(coords: np.ndarray) -> tuple[float, float]:
    """Spherical mean of lon/lat coordinates, via unit vectors.

    Averaging degrees directly breaks across the antimeridian; averaging the
    3D unit vectors does not.
    """
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    x = np.mean(np.cos(lat) * np.cos(lon))
    y = np.mean(np.cos(lat) * np.sin(lon))
    z = np.mean(np.sin(lat))
    norm = math.hypot(math.hypot(x, y), z)
    if norm < 1e-12:  # antipodally balanced input; fall back to the first vertex
        return float(coords[0, 0]), float(coords[0, 1])
    lat0 = math.degrees(math.asin(z / norm))
    lon0 = math.degrees(math.atan2(y, x))
    # Round a little so nearby calls share a cached transformer.
    return round(lon0, 6), round(lat0, 6)


def _project(geom, transformer):
    def _fn(coords):
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        out = np.column_stack([x, y])
        if not np.isfinite(out).all():
            raise ValueError(
                "Coordinate transform produced non-finite values; the geometry "
                "or buffer distance is too large for a single local projection."
            )
        return out

    return shapely.transform(geom, _fn, interleaved=False if False else True)


def _unwrap(coords: np.ndarray, lon0: float) -> np.ndarray:
    """Make longitudes continuous (no +/-180 jumps) in a frame centred on lon0."""
    lon = coords[:, 0].astype(float).copy()
    lat = np.clip(coords[:, 1].astype(float), -90.0, 90.0)
    lon[0] -= 360.0 * math.floor((lon[0] - lon0 + 180.0) / 360.0)
    if len(lon) > 1:
        step = np.diff(coords[:, 0].astype(float))
        step -= 360.0 * np.round(step / 360.0)
        lon[1:] = lon[0] + np.cumsum(step)
    return np.column_stack([lon, lat])


def _unwrap_ring(ring: LinearRing, lon0: float) -> LinearRing:
    coords = _unwrap(np.asarray(ring.coords), lon0)
    span = coords[-1, 0] - coords[0, 0]
    if abs(span) > 180.0:
        # The ring winds all the way around a pole: close it along the pole edge
        # so it stays a valid ring once cut at the dateline.
        pole = 90.0 if coords[:, 1].mean() >= 0 else -90.0
        cap = np.array(
            [
                [coords[-1, 0], pole],
                [coords[0, 0], pole],
                [coords[0, 0], coords[0, 1]],
            ]
        )
        coords = np.vstack([coords, cap])
    return LinearRing(coords)


def _unwrap_polygon(poly: Polygon, lon0: float) -> Polygon:
    return Polygon(
        _unwrap_ring(poly.exterior, lon0),
        [_unwrap_ring(r, lon0) for r in poly.interiors],
    )


def _rewrap(geom, lon0: float):
    """Cut an unwrapped geometry at the dateline and fold it back into [-180, 180]."""
    minx, _, maxx, _ = geom.bounds
    k0 = math.floor((minx + 180.0) / 360.0)
    k1 = math.floor((maxx + 180.0) / 360.0)
    parts = []
    for k in range(k0, k1 + 1):
        band = box(360.0 * k - 180.0, -90.0, 360.0 * k + 180.0, 90.0)
        piece = geom.intersection(band)
        if piece.is_empty:
            continue
        if k:
            piece = translate(piece, xoff=-360.0 * k)
        parts.append(piece)
    if not parts:
        return geom
    merged = unary_union(parts)
    polys = [g for g in shapely.get_parts(merged) if isinstance(g, Polygon)]
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys) if polys else merged


def buffer_m(geom, distance_m, quad_segs: int = 16, max_segment_m: float = 50_000.0):
    """Buffer a WGS84 (lon/lat) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        Any shapely geometry whose coordinates are longitude/latitude degrees in
        EPSG:4326.
    distance_m:
        Buffer distance in metres.  Negative values erode (polygons only).
    quad_segs:
        Segments per quarter circle used to approximate the round buffer cap.
    max_segment_m:
        Input edges longer than roughly this are densified before projecting, so
        that long edges keep their shape through the projection.

    Returns
    -------
    A Polygon or MultiPolygon in EPSG:4326.  Buffers crossing the antimeridian
    are returned split at +/-180; buffers enclosing a pole are closed along the
    +/-90 edge.
    """
    if geom is None or geom.is_empty:
        return geom

    coords = shapely.get_coordinates(geom)
    if coords.size == 0:
        return geom

    lon0, lat0 = _center(coords)

    # Reject cases where a single AEQD projection cannot stay well-conditioned.
    if abs(distance_m) > _MAX_RADIUS_M:
        raise ValueError(
            f"distance_m={distance_m} is too large for a local projection "
            f"(limit ~{_MAX_RADIUS_M:,.0f} m)."
        )

    work = geom
    if max_segment_m and max_segment_m > 0 and shapely.get_num_coordinates(geom) > 1:
        # Densify in degrees; ~111.32 km per degree of latitude is close enough
        # for choosing a vertex spacing.
        max_seg_deg = max_segment_m / 111_320.0
        if max_seg_deg > 0:
            work = shapely.segmentize(work, max_seg_deg)

    fwd, inv = _transformers(lon0, lat0)
    projected = _project(work, fwd)
    buffered = projected.buffer(distance_m, quad_segs=quad_segs)
    if buffered.is_empty:
        return buffered

    back = _project(buffered, inv)

    if isinstance(back, Polygon):
        unwrapped = _unwrap_polygon(back, lon0)
    else:
        unwrapped = MultiPolygon(
            [_unwrap_polygon(p, lon0) for p in shapely.get_parts(back)]
        )

    result = _rewrap(unwrapped, lon0)
    if not result.is_valid:
        result = result.buffer(0)
    return result