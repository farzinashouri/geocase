I couldn't execute a verification run in this environment (both file writes and Python execution were denied), so the module below is reviewed by hand rather than test-run.

```python
"""Split EPSG:4326 polygons that cross the antimeridian into pieces that do not.

The single public function is :func:`split_antimeridian`. Importing this
module has no side effects.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np
import shapely
from shapely.affinity import translate
from shapely.geometry import Polygon, box

__all__ = ["split_antimeridian"]

_HALF_TURN = 180.0
_FULL_TURN = 360.0


def _ring_xy(ring) -> np.ndarray:
    """Return the ring's (lon, lat) vertices as an (n, 2) float array."""
    return np.asarray(ring.coords, dtype=float)[:, :2]


def _crosses(xy: np.ndarray) -> bool:
    """True if any consecutive pair of vertices jumps by more than 180 degrees."""
    return bool(np.any(np.abs(np.diff(xy[:, 0])) > _HALF_TURN))


def _unwrap(xy: np.ndarray) -> np.ndarray:
    """Make longitudes continuous by adding multiples of 360 after each jump.

    The first vertex keeps its original longitude; later vertices are shifted so
    that no consecutive pair differs by more than 180 degrees. A closed ring
    that ends a full turn away from where it started winds around a pole, which
    has no unambiguous antimeridian split, so that case raises ``ValueError``.
    """
    out = xy.copy()
    out[:, 0] = np.unwrap(xy[:, 0], period=_FULL_TURN)
    if abs(out[-1, 0] - out[0, 0]) > 1e-9:
        raise ValueError(
            "ring winds around a pole; it has no unambiguous antimeridian split"
        )
    return out


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """Split a lon/lat polygon at the antimeridian.

    ``polygon`` is a shapely ``Polygon`` in EPSG:4326 with longitudes in
    [-180, 180]. A crossing is recognised by a jump of more than 180 degrees of
    longitude between consecutive vertices of any ring (shell or hole).

    Returns a list of valid polygons that together cover the same region of the
    Earth's surface, none of which crosses the antimeridian; pieces may touch
    it along an edge at longitude +180 or -180. A polygon with no crossing is
    returned unchanged as a one-element list.
    """
    rings = [polygon.exterior, *polygon.interiors]
    coords = [_ring_xy(ring) for ring in rings]
    if not any(_crosses(xy) for xy in coords):
        return [polygon]

    # 1. Unwrap every ring into a continuous longitude range, then shift each
    #    hole by whole turns so it sits inside the shell's range.
    shell = _unwrap(coords[0])
    shell_mean_lon = shell[:, 0].mean()
    holes = []
    for xy in coords[1:]:
        hole = _unwrap(xy)
        turns = round((shell_mean_lon - hole[:, 0].mean()) / _FULL_TURN)
        hole[:, 0] += turns * _FULL_TURN
        holes.append(hole)

    unwrapped = Polygon(shell, holes)
    if not unwrapped.is_valid:
        unwrapped = shapely.make_valid(unwrapped)

    # 2. Find every meridian of the form 180 + 360k strictly inside the
    #    unwrapped longitude range; these are the cut lines.
    minx, miny, maxx, maxy = unwrapped.bounds
    k_lo = math.floor((minx - _HALF_TURN) / _FULL_TURN)
    k_hi = math.ceil((maxx - _HALF_TURN) / _FULL_TURN)
    meridians = (_HALF_TURN + k * _FULL_TURN for k in range(k_lo, k_hi + 1))
    cuts = [m for m in meridians if minx < m < maxx]
    edges = [minx, *cuts, maxx]

    # 3. Clip the unwrapped polygon to each longitude band, then shift the band
    #    back by whole turns into [-180, 180].
    pieces: List[Polygon] = []
    for west, east in zip(edges[:-1], edges[1:]):
        band = box(west, miny - 1.0, east, maxy + 1.0)
        clipped = unwrapped.intersection(band)
        turns = math.floor(((west + east) / 2.0 + _HALF_TURN) / _FULL_TURN)
        if turns:
            clipped = translate(clipped, xoff=-turns * _FULL_TURN)
        for part in shapely.get_parts(clipped):
            if part.geom_type == "Polygon" and part.area > 0:
                pieces.append(part)
    return pieces
```