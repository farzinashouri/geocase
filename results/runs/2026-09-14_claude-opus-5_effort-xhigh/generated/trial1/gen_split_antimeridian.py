"""Antimeridian-safe splitting of EPSG:4326 polygons.

A polygon whose vertices are lon/lat degrees in ``[-180, 180]`` cannot represent
a region straddling the antimeridian without an artificial jump between
longitudes near ``+180`` and longitudes near ``-180``.  :func:`split_antimeridian`
undoes that jump (working in an unwrapped, unbounded longitude space), cuts the
resulting geometry along every meridian ``180 + 360k``, and maps each piece back
into ``[-180, 180]``.

The only public entry point is :func:`split_antimeridian`.  Importing this module
has no side effects.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_HALF = 180.0


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` into pieces that do not cross the antimeridian.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` in EPSG:4326 with
        longitudes in ``[-180, 180]``.  Consecutive vertices whose longitudes
        differ by more than 180 degrees are interpreted as a crossing of the
        antimeridian rather than as a jump the long way round the Earth.

    Returns
    -------
    list of Polygon
        Valid polygons that together cover exactly the same region of the
        Earth's surface as ``polygon``.  No returned polygon crosses the
        antimeridian; they may touch it along their ``±180`` edges.  A polygon
        that does not cross the antimeridian is returned unchanged as the only
        element of the list.

    Raises
    ------
    TypeError
        If ``polygon`` is not a :class:`~shapely.geometry.Polygon`.
    ValueError
        If a ring winds all the way around the Earth in longitude.  Such a ring
        encircles a pole, which lon/lat polygon geometry cannot represent
        unambiguously, so no meaningful split exists.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(
            "expected a shapely Polygon, got {!r}".format(type(polygon).__name__)
        )
    if polygon.is_empty:
        return [polygon]

    shell, changed = _unwrap_ring(polygon.exterior)
    lo = float(shell[:, 0].min())
    hi = float(shell[:, 0].max())

    holes = []
    for interior in polygon.interiors:
        hole, hole_changed = _unwrap_ring(interior)
        hole[:, 0], shift = _align(hole[:, 0], lo, hi)
        changed = changed or hole_changed or shift != 0
        holes.append(hole)

    unwrapped = Polygon(shell, holes)
    minx, _, maxx, _ = unwrapped.bounds
    bands = _bands(minx, maxx)

    # Nothing was rewrapped and everything lives inside a single 360-degree
    # band: the polygon never crosses the antimeridian, so hand it back as is.
    if not changed and len(bands) == 1:
        return [polygon]

    geom = _repair(unwrapped)
    _, miny, _, maxy = geom.bounds

    parts: List[Polygon] = []
    for k in bands:
        offset = k * _PERIOD
        clip = box(-_HALF + offset, miny - 1.0, _HALF + offset, maxy + 1.0)
        piece = geom.intersection(clip)
        if piece.is_empty:
            continue
        parts.extend(_polygons(translate(piece, xoff=-offset)))

    # Rings spanning more than 360 degrees of longitude wrap onto themselves;
    # dissolve the overlap so the pieces tile the region exactly once.
    if len(parts) > 1:
        total = sum(part.area for part in parts)
        merged = unary_union(parts)
        if merged.area < total - 1e-9 * max(total, 1.0):
            parts = _polygons(merged)

    return [poly for part in parts for poly in _polygons(_repair(part))]


def _unwrap(lons: Sequence[float]) -> Tuple[np.ndarray, bool]:
    """Remove ``±360`` jumps from a longitude sequence.

    Returns the unwrapped longitudes and whether any vertex was moved.  A step
    of exactly 180 degrees is ambiguous and is left alone.
    """
    values = np.asarray(lons, dtype=float)
    steps = np.diff(values)
    adjust = np.where(
        np.abs(steps) > _HALF, -_PERIOD * np.round(steps / _PERIOD), 0.0
    )
    if not adjust.any():
        return values, False
    return values + np.concatenate(([0.0], np.cumsum(adjust))), True


def _unwrap_ring(ring) -> Tuple[np.ndarray, bool]:
    """Unwrap one ring into continuous longitude space as an ``(n, 2)`` array."""
    coords = np.array(ring.coords, dtype=float)[:, :2]
    lons, changed = _unwrap(coords[:, 0])

    # The ring is closed, so the endpoints differ by an exact multiple of 360;
    # anything but zero means the ring circles a pole.
    winding = int(round((lons[-1] - lons[0]) / _PERIOD))
    if winding != 0:
        raise ValueError(
            "ring winds {:+d} times around the Earth in longitude; a polygon "
            "encircling a pole cannot be split at the antimeridian".format(winding)
        )
    lons[-1] = lons[0]

    out = np.empty_like(coords)
    out[:, 0] = lons
    out[:, 1] = coords[:, 1]
    return out, changed


def _align(lons: np.ndarray, ref_lo: float, ref_hi: float) -> Tuple[np.ndarray, int]:
    """Shift a hole by whole periods so it lands inside the shell's span."""
    lo = float(lons.min())
    hi = float(lons.max())
    k_lo = int(np.floor((ref_lo - hi) / _PERIOD)) - 1
    k_hi = int(np.ceil((ref_hi - lo) / _PERIOD)) + 1

    best_k = 0
    best_overlap = -np.inf
    for k in range(k_lo, k_hi + 1):
        offset = k * _PERIOD
        overlap = min(hi + offset, ref_hi) - max(lo + offset, ref_lo)
        if overlap > best_overlap or (overlap == best_overlap and abs(k) < abs(best_k)):
            best_k, best_overlap = k, overlap

    if best_k == 0:
        return lons, 0
    return lons + best_k * _PERIOD, best_k


def _bands(minx: float, maxx: float) -> List[int]:
    """Indices ``k`` of the bands ``[-180 + 360k, 180 + 360k]`` that are spanned."""
    k_lo = int(np.floor((minx + _HALF) / _PERIOD))
    k_hi = int(np.ceil((maxx + _HALF) / _PERIOD)) - 1
    if k_hi < k_lo:
        k_hi = k_lo
    return list(range(k_lo, k_hi + 1))


def _repair(geom: BaseGeometry) -> BaseGeometry:
    """Return an equivalent valid geometry."""
    return geom if geom.is_valid else make_valid(geom)


def _polygons(geom: BaseGeometry) -> List[Polygon]:
    """Flatten a geometry into its non-degenerate polygonal components."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom] if geom.area > 0.0 else []
    if hasattr(geom, "geoms"):
        return [poly for part in geom.geoms for poly in _polygons(part)]
    return []