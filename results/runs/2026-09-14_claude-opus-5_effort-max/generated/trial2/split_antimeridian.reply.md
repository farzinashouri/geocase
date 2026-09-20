I couldn't execute anything to verify it (the sandbox declined both the Python run and the scratch-file write), so this is reasoned-through but unrun.

```python
"""Split polygons that cross the antimeridian into antimeridian-free parts.

The only public name is :func:`split_antimeridian`.
"""

from __future__ import annotations

import math
from typing import NamedTuple, Sequence

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_ANTIMERIDIAN = 180.0


class _Ring(NamedTuple):
    """A ring whose longitudes have been made continuous."""

    coords: list
    crossed: bool  # at least one edge jumped the antimeridian
    net_shift: float  # non-zero when the ring winds around the globe


def _unwrap(coords: Sequence[Sequence[float]]) -> _Ring:
    """Undo the [-180, 180] wrap of a closed ring.

    Any edge spanning more than half the globe is read as an antimeridian
    jump and is cancelled by shifting the remainder of the ring by a turn.
    """
    points = [tuple(c) for c in coords]
    out = [points[0]]
    shift = 0.0
    crossed = False
    for prev, cur in zip(points, points[1:]):
        step = cur[0] - prev[0]
        if step > _ANTIMERIDIAN:
            shift -= _PERIOD
            crossed = True
        elif step < -_ANTIMERIDIAN:
            shift += _PERIOD
            crossed = True
        out.append((cur[0] + shift,) + cur[1:])
    return _Ring(out, crossed, shift)


def _midspan(coords: Sequence[Sequence[float]]) -> float:
    lons = [c[0] for c in coords]
    return 0.5 * (min(lons) + max(lons))


def _align(coords: list, target: float) -> list:
    """Shift a hole by whole turns onto the same lap as its shell."""
    turns = round((target - _midspan(coords)) / _PERIOD)
    if turns == 0:
        return coords
    return [(c[0] + turns * _PERIOD,) + tuple(c[1:]) for c in coords]


def _clamp(polygon: Polygon) -> Polygon:
    """Pull coordinates back inside [-180, 180] after the inverse shift.

    Clipping and shifting are exact bar the odd unit in the last place, so
    this only ever moves a vertex sitting on the cut itself.
    """

    def ring(coords):
        return [
            (min(_ANTIMERIDIAN, max(-_ANTIMERIDIAN, c[0])),) + tuple(c[1:])
            for c in coords
        ]

    return Polygon(
        ring(polygon.exterior.coords),
        [ring(hole.coords) for hole in polygon.interiors],
    )


def _polygons(geom: BaseGeometry) -> list:
    """Collect the positive-area polygons of any geometry."""
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom] if geom.area > 0.0 else []
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [p for part in geom.geoms for p in _polygons(part)]
    return []  # points and lines from tangential contact carry no area


def split_antimeridian(polygon: Polygon) -> list:
    """Split a lon/lat polygon along the antimeridian.

    ``polygon`` is read as EPSG:4326 with longitudes in [-180, 180]. It
    crosses the antimeridian when consecutive vertices jump between +180 and
    -180, which is taken to mean any edge spanning more than 180 degrees of
    longitude. A polygon genuinely meant to span more than half the globe in
    one edge is indistinguishable from a crossing one and has to be
    densified by the caller first.

    Returns a list of valid polygons covering exactly the same region, each
    within [-180, 180] and touching the antimeridian at its edge only. A
    polygon that does not cross is returned unchanged as a single element.

    Raises ``ValueError`` for a ring that winds around the globe, which is
    how a polygon enclosing a pole shows up here: it has no planar lon/lat
    extent to cut.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        return [polygon]

    shell = _unwrap(polygon.exterior.coords)
    holes = [_unwrap(hole.coords) for hole in polygon.interiors]
    for ring in (shell, *holes):
        if ring.net_shift != 0.0:
            raise ValueError(
                "polygon ring winds around the globe in longitude; a ring "
                "enclosing a pole cannot be split at the antimeridian"
            )
    if not (shell.crossed or any(hole.crossed for hole in holes)):
        return [polygon]

    target = _midspan(shell.coords)
    work = Polygon(shell.coords, [_align(hole.coords, target) for hole in holes])
    if not work.is_valid:
        work = make_valid(work)  # a self-intersection would abort the clip
    if work.is_empty:
        return []

    xmin, ymin, xmax, ymax = work.bounds
    first = math.floor((xmin + _ANTIMERIDIAN) / _PERIOD)
    last = math.floor((xmax + _ANTIMERIDIAN) / _PERIOD)
    parts = []
    for lap in range(first, last + 1):
        centre = lap * _PERIOD
        band = box(centre - _ANTIMERIDIAN, ymin, centre + _ANTIMERIDIAN, ymax)
        for piece in _polygons(work.intersection(band)):
            parts.append(_clamp(translate(piece, xoff=-centre)))
    return parts
```