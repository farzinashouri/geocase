I couldn't run a quick self-test (shell approval was declined), so this is written to be conservative. Note the one documented out-of-scope case: a ring that genuinely winds around a pole (a cap whose boundary circles the globe) can't be represented by clipping alone, so it raises `ValueError` rather than silently returning a wrong region; pole polygons already drawn with a ±180 seam (the usual Antarctica encoding) are recognised and returned unchanged.

```python
"""Split shapely polygons that straddle the antimeridian.

The single public entry point is :func:`split_antimeridian`.  Importing this
module has no side effects.

The approach is "unwrap, then clip".  Each ring is walked vertex by vertex and
whenever a step in longitude exceeds 180 degrees -- the signature of a jump
across the antimeridian -- a multiple of 360 is accumulated so that the ring
becomes continuous in an unbounded longitude space.  The resulting planar
polygon is then intersected with the vertical lunes ``[360k - 180, 360k + 180]``
and each piece is translated back by ``-360k``.
"""

from __future__ import annotations

import math
from typing import Iterator, List

import numpy as np
import shapely
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["split_antimeridian"]

_PERIOD = 360.0
_HALF_PERIOD = 180.0

# Slack used when testing whether a polygon already fits inside [-180, 180] and
# when closing rings.  1e-9 degrees is roughly 0.1 mm on the ground, i.e. far
# below the precision of any coordinate this function is likely to see.
_TOL = 1e-9


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split ``polygon`` at the antimeridian.

    Parameters
    ----------
    polygon
        A shapely :class:`~shapely.geometry.Polygon` in EPSG:4326 with
        longitudes in ``[-180, 180]``.  It may cross the antimeridian, in which
        case consecutive vertices jump between values near ``+180`` and values
        near ``-180``.  Interior rings are supported and may cross too.

    Returns
    -------
    list of Polygon
        Valid polygons that together cover the same region of the Earth's
        surface as the input and that touch the antimeridian only along their
        edge.  A polygon that does not cross the antimeridian is returned as a
        single-element list holding the original object, unchanged.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If a ring winds all the way around the globe, i.e. the polygon contains
        a pole without being drawn with a seam along the antimeridian.  Such a
        region cannot be recovered from its longitude/latitude vertices by
        clipping alone, so it is out of scope here.

    Notes
    -----
    A polygon that spans more than 360 degrees of longitude already covers some
    meridians twice; the returned pieces then overlap, mirroring the input.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(
            "expected a shapely Polygon, got {}".format(type(polygon).__name__)
        )
    if polygon.is_empty:
        return [polygon]

    unwrapped = _unwrap_polygon(polygon)
    min_lon, min_lat, max_lon, max_lat = unwrapped.bounds
    if min_lon >= -_HALF_PERIOD - _TOL and max_lon <= _HALF_PERIOD + _TOL:
        # Either no jump was found, or the only jumps were zero-length seam
        # segments along the antimeridian: the polygon already lies in one lune.
        return [polygon]

    if not unwrapped.is_valid:
        unwrapped = shapely.make_valid(unwrapped)

    # Indices of the lunes [360k - 180, 360k + 180] that the polygon reaches
    # into.  The tolerance keeps a polygon that merely touches a lune boundary
    # from spawning a degenerate clip.
    first = math.floor((min_lon + _HALF_PERIOD + _TOL) / _PERIOD)
    last = math.floor((max_lon + _HALF_PERIOD - _TOL) / _PERIOD)

    pieces: List[Polygon] = []
    for index in range(first, max(last, first) + 1):
        offset = index * _PERIOD
        lune = box(
            offset - _HALF_PERIOD, min_lat - 1.0, offset + _HALF_PERIOD, max_lat + 1.0
        )
        clipped = unwrapped.intersection(lune)
        if clipped.is_empty:
            continue
        if offset:
            clipped = translate(clipped, xoff=-offset)
        pieces.extend(_polygonal_parts(_clamp_longitude(clipped)))
    return pieces


def _unwrap_polygon(polygon: Polygon) -> Polygon:
    """Return ``polygon`` with every ring made continuous in longitude."""
    shell = _unwrap_ring(polygon.exterior)
    shell_centre = 0.5 * (shell[:, 0].min() + shell[:, 0].max())

    holes = []
    for interior in polygon.interiors:
        ring = _unwrap_ring(interior)
        # A ring is unwrapped relative to its own first vertex, so a hole can
        # land a whole period away from the shell that contains it.
        centre = 0.5 * (ring[:, 0].min() + ring[:, 0].max())
        shift = round((shell_centre - centre) / _PERIOD) * _PERIOD
        if shift:
            ring[:, 0] += shift
        holes.append(ring)
    return Polygon(shell, holes)


def _unwrap_ring(ring) -> np.ndarray:
    """Return the coordinates of ``ring`` with antimeridian jumps undone.

    The ring must close back onto itself once unwrapped.  If it does not, it
    encircles the globe; a second attempt is made treating exact ``+180`` to
    ``-180`` steps as zero-length seam segments rather than jumps, which is how
    pole-covering polygons are conventionally drawn.
    """
    coords = np.asarray(ring.coords, dtype=float)
    lons = coords[:, 0]

    for keep_seams in (False, True):
        unwrapped_lons = lons + _wrap_offsets(lons, keep_seams)
        if abs(unwrapped_lons[-1] - unwrapped_lons[0]) <= _TOL:
            out = coords.copy()
            out[:, 0] = unwrapped_lons
            out[-1] = out[0]  # keep the closure exact
            return out

    raise ValueError(
        "ring winds around the globe, so the polygon contains a pole; "
        "split_antimeridian cannot recover such a region from its vertices"
    )


def _wrap_offsets(lons: np.ndarray, keep_seams: bool) -> np.ndarray:
    """Multiples of 360 to add to each longitude to make the sequence continuous."""
    steps = np.diff(lons)
    offsets = np.zeros_like(steps)
    offsets[steps > _HALF_PERIOD] = -_PERIOD
    offsets[steps < -_HALF_PERIOD] = _PERIOD
    if keep_seams and steps.size:
        seam = (np.abs(lons[:-1]) == _HALF_PERIOD) & (np.abs(lons[1:]) == _HALF_PERIOD)
        offsets[seam] = 0.0
    return np.concatenate(([0.0], np.cumsum(offsets)))


def _clamp_longitude(geom: BaseGeometry) -> BaseGeometry:
    """Pull longitudes back inside [-180, 180] after the round trip through 360."""
    min_lon, _, max_lon, _ = geom.bounds
    if min_lon >= -_HALF_PERIOD and max_lon <= _HALF_PERIOD:
        return geom

    def clamp(coords: np.ndarray) -> np.ndarray:
        coords = coords.copy()
        coords[:, 0] = np.clip(coords[:, 0], -_HALF_PERIOD, _HALF_PERIOD)
        return coords

    return shapely.transform(geom, clamp, include_z=geom.has_z)


def _polygonal_parts(geom: BaseGeometry) -> List[Polygon]:
    """Return the non-degenerate, valid polygons contained in ``geom``.

    Clipping can hand back lines or points where the polygon only grazes a lune
    boundary; those carry no area and are dropped.
    """
    parts: List[Polygon] = []
    for part in _flatten(geom):
        if not isinstance(part, Polygon) or part.area <= 0.0:
            continue
        if part.is_valid:
            parts.append(part)
            continue
        for repaired in _flatten(shapely.make_valid(part)):
            if isinstance(repaired, Polygon) and repaired.area > 0.0:
                parts.append(repaired)
    return parts


def _flatten(geom: BaseGeometry) -> Iterator[BaseGeometry]:
    """Yield the non-empty single-part geometries inside ``geom``."""
    if geom is None or geom.is_empty:
        return
    if hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _flatten(part)
    else:
        yield geom
```