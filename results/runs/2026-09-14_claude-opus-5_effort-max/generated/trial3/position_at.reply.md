```python
"""Estimate a ship's position between GPS fixes.

The ship is assumed to travel between consecutive fixes along the shortest
path on the WGS84 ellipsoid (a geodesic) at constant ground speed.  The
position at an intermediate time is therefore the point that lies the
corresponding fraction of the geodesic distance from the earlier fix.

Interpolating longitude and latitude independently is tempting but wrong: it
breaks across the antimeridian (179.9 to -179.9 would sweep the long way
around the planet) and it drifts off the true track at high latitudes, where a
degree of longitude is much shorter than a degree of latitude.  Working in
distance-and-azimuth space avoids both problems, so results hold up anywhere
on the ocean, including the Southern Ocean and the Bering Strait.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return the shared WGS84 geodesic calculator.

    Built on first use rather than at import time, so importing this module
    has no side effects.
    """
    return Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _point(fix: Fix) -> Tuple[float, float]:
    """Return a fix's position as a normalized ``(lon, lat)`` tuple."""
    lon, lat = float(fix[1]), float(fix[2])
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"latitude out of range: {lat!r}")
    return (_normalize_lon(lon), lat)


def _bracket(fixes: Sequence[Fix], t: float) -> Tuple[int, int]:
    """Return indices ``(i, i + 1)`` of the fixes bracketing ``t``.

    Assumes ``fixes`` is sorted by timestamp and that
    ``fixes[0][0] <= t <= fixes[-1][0]``.  With duplicate timestamps, ``i`` is
    the last index whose timestamp is ``<= t``.
    """
    lo, hi = 0, len(fixes) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if float(fixes[mid][0]) <= t:
            lo = mid
        else:
            hi = mid
    return lo, hi


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Estimate the ship's position at time ``t``.

    Args:
        fixes: GPS fixes as ``(timestamp, lon, lat)``, sorted chronologically.
            Timestamps are Unix seconds; positions are WGS84 degrees.  The
            caller is responsible for the sort order; it is not re-verified.
        t: Unix timestamp between the first and last fix, inclusive.

    Returns:
        The interpolated ``(lon, lat)`` in WGS84 degrees, longitude wrapped
        into [-180, 180).

    Raises:
        ValueError: if ``fixes`` is empty, ``t`` is not finite, or ``t`` lies
            outside the time span covered by ``fixes``.
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes must contain at least one fix")

    t = float(t)
    if not math.isfinite(t):
        raise ValueError(f"t must be a finite timestamp, got {t!r}")

    first, last = fixes[0], fixes[-1]
    t_first, t_last = float(first[0]), float(last[0])
    if not (t_first <= t <= t_last):
        raise ValueError(
            f"t={t!r} is outside the fix range [{t_first!r}, {t_last!r}]"
        )

    # Snap to the endpoints so exact-hit queries are exact, not near-misses.
    if t == t_first:
        return _point(first)
    if t == t_last:
        return _point(last)

    i, j = _bracket(fixes, t)
    start, end = fixes[i], fixes[j]
    t_start, t_end = float(start[0]), float(end[0])

    if t == t_start or t_end == t_start:
        # Exact hit on an interior fix, or a zero-length interval left by
        # duplicate timestamps: the earlier fix is the answer either way.
        return _point(start)
    if t == t_end:
        return _point(end)

    lon1, lat1 = _point(start)
    lon2, lat2 = _point(end)

    # Azimuth and distance of the geodesic between the bracketing fixes; this
    # is what makes antimeridian and high-latitude segments come out right.
    azimuth, _, distance = _geod().inv(lon1, lat1, lon2, lat2)
    if distance == 0.0:
        return (lon1, lat1)

    fraction = (t - t_start) / (t_end - t_start)
    lon, lat, _ = _geod().fwd(lon1, lat1, azimuth, distance * fraction)
    return (_normalize_lon(lon), lat)
```