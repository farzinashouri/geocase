"""Split EPSG:4326 polygons that cross the antimeridian (the +/-180 degree meridian).

Public API: :func:`split_antimeridian`.

A polygon "crosses" the antimeridian when two consecutive vertices of one of
its rings jump between longitudes near +180 and near -180, i.e. the edge is
meant to take the short way round the back of the globe rather than the long
way across the map.  Such a ring is *unwrapped* into a continuous longitude
range (170 -> 190 instead of 170 -> -170), cut into 360-degree-wide windows,
and every piece is shifted back into [-180, 180].  The exterior and each hole
are processed independently and recombined with a planar difference, so holes
may cross the antimeridian as well, and the exterior may even be the full
world box with a hole straddling +/-180.

Importing this module has no side effects.
"""

from __future__ import annotations

from math import floor
from typing import List

import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

_HALF_TURN = 180.0
_FULL_TURN = 360.0
# Longitudes this close to +/-180 after re-wrapping are snapped exactly onto the
# antimeridian, so callers can rely on longitudes staying inside [-180, 180].
_SNAP_EPS = 1e-9


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` (EPSG:4326, longitude/latitude) at the antimeridian.

    Parameters
    ----------
    polygon
        A shapely ``Polygon`` with longitudes in [-180, 180].  Consecutive
        vertices whose longitudes differ by more than 180 degrees are read as
        an edge crossing the antimeridian.  A ``MultiPolygon`` is accepted as
        well and handled part by part.

    Returns
    -------
    list of Polygon
        Valid polygons that together cover exactly the same region of the
        Earth's surface, none of which crosses the antimeridian; pieces may
        touch it along their boundary.  A polygon that does not cross the
        antimeridian is returned as ``[polygon]`` (the very same object).

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely (Multi)Polygon.
    ValueError
        If a ring winds all the way around a pole (net 360 degrees of
        longitude); such a ring does not describe a well-defined region in
        this representation.
    """
    if isinstance(polygon, MultiPolygon):
        pieces: List[Polygon] = []
        for part in polygon.geoms:
            pieces.extend(split_antimeridian(part))
        return pieces
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    rings = [polygon.exterior, *polygon.interiors]
    if not any(_crosses(_ring_xy(ring)[:, 0]) for ring in rings):
        return [polygon]

    shell = shapely.union_all(_split_ring(polygon.exterior))
    holes = [piece for ring in polygon.interiors for piece in _split_ring(ring)]
    if holes:
        shell = shapely.difference(shell, shapely.union_all(holes))

    pieces = _polygons(shell)
    pieces.sort(key=lambda p: p.bounds[:2])
    return pieces


def _ring_xy(ring) -> np.ndarray:
    """Ring coordinates as an (N, 2) float array (any Z is dropped)."""
    return np.asarray(ring.coords, dtype=float)[:, :2]


def _crosses(lons: np.ndarray) -> bool:
    """True if any consecutive pair of longitudes jumps by more than 180 degrees."""
    return bool(np.any(np.abs(np.diff(lons)) > _HALF_TURN))


def _unwrap(xy: np.ndarray) -> np.ndarray:
    """Make a ring's longitudes continuous by adding +/-360 after each jump."""
    dx = np.diff(xy[:, 0])
    step = np.where(
        dx > _HALF_TURN, -_FULL_TURN, np.where(dx < -_HALF_TURN, _FULL_TURN, 0.0)
    )
    shift = np.concatenate(([0.0], np.cumsum(step)))
    if shift[-1] != 0.0:
        raise ValueError(
            "ring winds around a pole (net longitude change of "
            f"{shift[-1]:+g} degrees); cannot split such a polygon"
        )
    out = xy.copy()
    out[:, 0] += shift
    return out


def _polygons(geom: BaseGeometry) -> List[Polygon]:
    """Non-empty, positive-area Polygon parts of ``geom`` (recursively)."""
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom] if geom.area > 0.0 else []
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        parts: List[Polygon] = []
        for part in geom.geoms:
            parts.extend(_polygons(part))
        return parts
    return []


def _as_valid_area(geom: BaseGeometry) -> BaseGeometry:
    """A valid polygonal geometry covering the area that ``geom`` describes."""
    if not geom.is_valid:
        geom = shapely.make_valid(geom)
    parts = _polygons(geom)
    if len(parts) == 1:
        return parts[0]
    return shapely.union_all(parts)


def _shift_lon(geom: BaseGeometry, offset: float) -> BaseGeometry:
    """Translate ``geom`` along the longitude axis by ``offset`` degrees."""
    if offset == 0.0:
        return geom
    return shapely.transform(geom, lambda xy: xy + np.array([offset, 0.0]))


def _snap_to_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Snap longitudes within ``_SNAP_EPS`` of +/-180 exactly onto +/-180."""

    def snap(xy: np.ndarray) -> np.ndarray:
        xy = xy.copy()
        lon = xy[:, 0]
        lon[np.abs(lon - _HALF_TURN) <= _SNAP_EPS] = _HALF_TURN
        lon[np.abs(lon + _HALF_TURN) <= _SNAP_EPS] = -_HALF_TURN
        return xy

    return shapely.transform(geom, snap)


def _split_ring(ring) -> List[Polygon]:
    """Area enclosed by ``ring``, cut at the antimeridian and re-wrapped to [-180, 180].

    The ring is unwrapped into a continuous longitude range, then each
    360-degree window it overlaps is shifted onto [-180, 180] and clipped
    to that window.  Pieces from different windows never overlap, so they
    can simply be collected together.
    """
    area = _as_valid_area(Polygon(_unwrap(_ring_xy(ring))))
    if area.is_empty:
        return []
    xmin, ymin, xmax, ymax = area.bounds
    first = floor((xmin + _HALF_TURN + _SNAP_EPS) / _FULL_TURN)
    last = floor((xmax + _HALF_TURN - _SNAP_EPS) / _FULL_TURN)
    window = shapely.box(-_HALF_TURN, ymin - 1.0, _HALF_TURN, ymax + 1.0)
    pieces: List[Polygon] = []
    for k in range(first, last + 1):
        shifted = _shift_lon(area, -k * _FULL_TURN)
        clipped = _snap_to_antimeridian(shapely.intersection(shifted, window))
        pieces.extend(_polygons(_as_valid_area(clipped)))
    return pieces