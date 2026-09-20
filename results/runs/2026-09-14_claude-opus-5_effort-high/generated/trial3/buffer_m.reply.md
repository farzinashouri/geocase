```python
"""Accurate metric buffering of geometries expressed in EPSG:4326 (WGS84 lon/lat).

``buffer_m(geom, distance_m)`` offsets a lon/lat geometry by a distance given in
metres and returns the result in lon/lat.  Instead of using one global
projection (which is metrically faithful only in a narrow band), each piece of
the input is buffered in an azimuthal-equidistant projection centred on that
piece, so the result is equally good at the equator, at high latitudes, over the
poles and across the antimeridian.

Conventions and limits
----------------------
* Edges are read as straight lines in lon/lat (the plate-carree reading of the
  source CRS).  They are densified before projection so that shape is preserved.
* Input crossing the antimeridian is handled by unwrapping longitudes along each
  coordinate sequence (each edge takes the short way round).  Output crossing it
  is split into a MultiPolygon at +/-180; output covering a pole is closed along
  lat = +/-90.
* Large inputs are cut into tiles of a few hundred km before buffering.  A
  positive buffer distributes over a union, so tiling changes nothing except the
  accuracy: residual distortion of the local projection stays below ~1e-3 of the
  buffer distance.  Negative distances (erosion) do not distribute over a union,
  so they are buffered as a single piece and are only accurate for inputs whose
  extent is at most a few hundred kilometres.
* A distance at or beyond half the Earth's circumference returns the whole
  world; buffers of a large fraction of the planet are approximate.

Depends on shapely >= 2.0, pyproj and numpy.  Importing the module has no side
effects (projection objects are built lazily and cached).
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from pyproj import CRS, Transformer
from shapely import get_coordinates
from shapely.affinity import translate
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["buffer_m"]

_WGS84 = "EPSG:4326"
_A = 6378137.0                          # WGS84 semi-major axis (m)
_R = 6371008.8                          # mean Earth radius (m)
_M_PER_DEG = math.pi * _R / 180.0       # ~111195 m, for rough metric <-> degree work
_HALF_CIRCUMFERENCE = math.pi * _A      # a buffer this large covers the planet
_TILE_M = 400_000.0                     # max tile size -> ~1e-3 relative distortion
_MAX_TILES = 4096                       # safety valve for planet-sized inputs
_MIN_SEG_M = 5_000.0                    # densification bounds
_MAX_SEG_M = 200_000.0
_MAX_SPLITS_PER_EDGE = 10_000


# --------------------------------------------------------------------------- #
# projections
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=512)
def _transformers(lon0, lat0):
    """Forward/inverse transformers for an AEQD projection centred on lon0/lat0."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs"
    )
    return (
        Transformer.from_crs(_WGS84, aeqd, always_xy=True),
        Transformer.from_crs(aeqd, _WGS84, always_xy=True),
    )


def _apply(transformer, coords):
    if not coords:
        return []
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    ox, oy = transformer.transform(xs, ys)
    return [(x, y) for x, y in zip(ox, oy) if math.isfinite(x) and math.isfinite(y)]


# --------------------------------------------------------------------------- #
# generic coordinate rewriting
# --------------------------------------------------------------------------- #
def _map_coords(geom, fn):
    """Rebuild ``geom`` with every coordinate sequence passed through ``fn``.

    ``fn`` takes and returns a list of (x, y) tuples and may change its length.
    """
    if geom.is_empty:
        return geom
    kind = geom.geom_type
    if kind == "Point":
        pts = fn([(geom.x, geom.y)])
        return Point(pts[0]) if pts else Point()
    if kind == "LineString":
        return LineString(fn(list(geom.coords)))
    if kind == "LinearRing":
        return LinearRing(fn(list(geom.coords)))
    if kind == "Polygon":
        shell = fn(list(geom.exterior.coords))
        holes = [fn(list(r.coords)) for r in geom.interiors]
        holes = [h for h in holes if len(h) >= 4]
        if len(shell) < 4:
            return Polygon()
        return Polygon(shell, holes)
    if kind in ("MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"):
        parts = [_map_coords(g, fn) for g in geom.geoms]
        parts = [p for p in parts if not p.is_empty]
        if not parts:
            return GeometryCollection()
        if kind == "MultiPoint":
            return MultiPoint(parts)
        if kind == "MultiLineString":
            return MultiLineString(parts)
        if kind == "MultiPolygon":
            return MultiPolygon(parts)
        return GeometryCollection(parts)
    raise TypeError(f"unsupported geometry type: {kind}")


def _wrap180(delta):
    return (delta + 180.0) % 360.0 - 180.0


def _unwrap_seq(coords, anchor):
    """Make longitudes continuous: each step takes the short way round."""
    out = []
    prev = None
    for c in coords:
        lon, lat = float(c[0]), float(c[1])
        lon = anchor + _wrap180(lon - anchor) if prev is None else prev + _wrap180(lon - prev)
        prev = lon
        out.append((lon, lat))
    return out


def _densify_seq(coords, step_deg):
    if len(coords) < 2 or step_deg <= 0:
        return coords
    out = [coords[0]]
    for (plon, plat), (lon, lat) in zip(coords, coords[1:]):
        span = max(abs(lon - plon), abs(lat - plat))
        n = min(int(math.ceil(span / step_deg)) - 1, _MAX_SPLITS_PER_EDGE)
        for k in range(1, n + 1):
            t = k / (n + 1.0)
            out.append((plon + (lon - plon) * t, plat + (lat - plat) * t))
        out.append((lon, lat))
    return out


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _spherical_center(coords):
    """Mean direction of the vertices on the unit sphere (antimeridian-safe)."""
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    x = float(np.mean(np.cos(lat) * np.cos(lon)))
    y = float(np.mean(np.cos(lat) * np.sin(lon)))
    z = float(np.mean(np.sin(lat)))
    if math.hypot(x, y, z) < 1e-12:          # vertices cancel out; any centre will do
        return 0.0, 0.0
    return math.degrees(math.atan2(y, x)), math.degrees(math.atan2(z, math.hypot(x, y)))


def _polygons(geom):
    if geom is None or geom.is_empty:
        return []
    kind = geom.geom_type
    if kind == "Polygon":
        return [geom]
    if kind == "MultiPolygon":
        return list(geom.geoms)
    if kind == "GeometryCollection":
        return [p for g in geom.geoms for p in _polygons(g)]
    return []


def _clean(geom):
    if geom.is_empty or geom.is_valid:
        return geom
    return geom.buffer(0)


def _tiles(geom):
    """Cut ``geom`` into pieces small enough for a local projection."""
    minx, miny, maxx, maxy = geom.bounds
    cell = _TILE_M / _M_PER_DEG                      # conservative: degrees on both axes
    nx = max(1, int(math.ceil((maxx - minx) / cell)))
    ny = max(1, int(math.ceil((maxy - miny) / cell)))
    if nx * ny > _MAX_TILES:
        cell *= math.sqrt(nx * ny / _MAX_TILES)
        nx = max(1, int(math.ceil((maxx - minx) / cell)))
        ny = max(1, int(math.ceil((maxy - miny) / cell)))
    if nx == 1 and ny == 1:
        return [geom]
    pieces = []
    for i in range(nx):
        for j in range(ny):
            cell_box = box(
                minx + i * cell,
                miny + j * cell,
                min(minx + (i + 1) * cell, maxx),
                min(miny + (j + 1) * cell, maxy),
            )
            piece = geom.intersection(cell_box)
            if not piece.is_empty:
                pieces.append(piece)
    return pieces or [geom]


def _ring_to_lonlat(ring, inv, anchor_lon, north_pt):
    """Inverse-project one projected ring, closing it over a pole if it winds."""
    pts = _apply(inv, list(ring.coords))
    if len(pts) < 4:
        return None
    pts = _unwrap_seq(pts, anchor_lon)
    pts = [(lon, min(90.0, max(-90.0, lat))) for lon, lat in pts]
    if abs(pts[-1][0] - pts[0][0]) > 180.0:           # the ring encircles a pole
        try:
            cap = 90.0 if Polygon(ring).contains(north_pt) else -90.0
        except Exception:                             # degenerate ring; fall back on latitude
            cap = 90.0 if pts[0][1] > 0 else -90.0
        pts = pts + [(pts[-1][0], cap), (pts[0][0], cap)]
    return pts


def _buffer_piece(piece, distance_m, quad_segs):
    if piece.is_empty:
        return None
    centre = piece.centroid
    if centre.is_empty:
        minx, miny, maxx, maxy = piece.bounds
        clon, clat = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    else:
        clon, clat = centre.x, centre.y

    fwd, inv = _transformers(round(_wrap180(clon), 6), round(clat, 6))
    projected = _map_coords(piece, lambda cs: _apply(fwd, cs))
    if projected.is_empty:
        return None

    buffered = projected.buffer(distance_m, quad_segs=quad_segs)
    polys = _polygons(buffered)
    if not polys:
        return None

    north_pt = Point(*fwd.transform(0.0, 90.0))
    out = []
    for poly in polys:
        shell = _ring_to_lonlat(poly.exterior, inv, clon, north_pt)
        if shell is None:
            continue
        holes = [_ring_to_lonlat(r, inv, clon, north_pt) for r in poly.interiors]
        holes = [h for h in holes if h is not None and len(h) >= 4]
        out.append(_clean(Polygon(shell, holes)))
    out = [g for g in out if not g.is_empty]
    return unary_union(out) if out else None


def _split_antimeridian(geom):
    """Fold an unwrapped-longitude geometry back into [-180, 180]."""
    minx, _, maxx, _ = geom.bounds
    kmin = int(math.floor((minx + 180.0) / 360.0))
    kmax = int(math.floor((maxx + 180.0) / 360.0))
    if kmin == 0 and kmax == 0:
        return geom
    parts = []
    for k in range(kmin, kmax + 1):
        band = box(360.0 * k - 180.0, -90.0, 360.0 * k + 180.0, 90.0)
        piece = geom.intersection(band)
        polys = _polygons(piece)
        if polys:
            parts.append(translate(unary_union(polys), xoff=-360.0 * k))
    return unary_union(parts) if parts else geom


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def buffer_m(geom, distance_m, quad_segs=16):
    """Buffer a WGS84 lon/lat geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom : shapely geometry with longitude/latitude coordinates (EPSG:4326).
    distance_m : offset in metres; positive expands, negative erodes.
    quad_segs : segments per quarter circle used to approximate round joins.

    Returns
    -------
    The buffered geometry, again in EPSG:4326.  For a non-zero distance this is
    a ``Polygon`` or ``MultiPolygon`` (a MultiPolygon when the result straddles
    the antimeridian).  A zero distance returns the input unchanged.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be finite")
    if geom.is_empty or distance_m == 0.0:
        return geom
    if distance_m >= _HALF_CIRCUMFERENCE:
        return box(-180.0, -90.0, 180.0, 90.0)

    coords = get_coordinates(geom)
    if len(coords) == 0:
        return geom
    lon0, _ = _spherical_center(coords)

    # Work in a contiguous longitude frame, with edges short enough that their
    # lon/lat shape survives projection.
    step_deg = min(max(abs(distance_m) / 4.0, _MIN_SEG_M), _MAX_SEG_M) / _M_PER_DEG
    work = _map_coords(geom, lambda cs: _densify_seq(_unwrap_seq(cs, lon0), step_deg))
    if work.is_empty:
        return geom

    # A positive buffer distributes over a union, so tiling is exact; erosion
    # does not, so it stays in one piece.
    pieces = _tiles(work) if distance_m > 0 else [work]

    buffered = [b for b in (_buffer_piece(p, distance_m, quad_segs) for p in pieces)
                if b is not None and not b.is_empty]
    if not buffered:
        return Polygon()

    merged = _clean(unary_union(buffered))
    if merged.is_empty:
        return merged
    return _split_antimeridian(merged)
```