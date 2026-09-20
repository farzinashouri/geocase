Geodesic interpolation on the WGS84 ellipsoid — linear lon/lat blending breaks at the antimeridian and drifts from the true path at high latitudes, so this brackets `t` with a binary search and walks the geodesic between the two fixes.

```python
"""Estimate a ship's position between consecutive GPS fixes.

The track is modelled as a sequence of WGS84 geodesic legs travelled at
constant speed. Between the two fixes bracketing ``t`` the position is found by
taking the initial azimuth and geodesic distance of the leg (``Geod.inv``) and
stepping the time-fraction of that distance along it (``Geod.fwd``).

Why not interpolate longitude and latitude linearly: it produces gross errors on
exactly the legs a ship sails. A leg crossing the antimeridian (e.g. 179E -> 179W)
is read as a 358-degree backwards jump across the whole Pacific, and at high
latitudes a lon/lat blend traces neither the great circle nor the rhumb line,
straying by kilometres on a long leg. Working in azimuth/distance on the
ellipsoid keeps both cases correct, including near the poles.

The geodesic (shortest path) is the assumption here rather than a rhumb line;
for the short legs typical of AIS/GPS logging the two are indistinguishable, and
for long gaps the geodesic is the standard reconstruction. Interpolation error
is dominated by how far apart the fixes are, not by the maths: a ship that
manoeuvred between two distant fixes was never on this path.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (unix_seconds, lon, lat)

_GEOD = Geod(ellps="WGS84")


def _time_of(fix: Fix) -> float:
    return fix[0]


def _wrap_lon(lon: float) -> float:
    """Normalise a longitude to (-180, 180]."""
    return math.remainder(float(lon), 360.0)


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the ship's estimated ``(lon, lat)`` at time ``t``.

    Parameters
    ----------
    fixes:
        Chronologically sorted ``(timestamp, lon, lat)`` tuples. Timestamps are
        Unix seconds; ``lon``/``lat`` are WGS84 degrees. Repeated timestamps are
        tolerated (the last fix carrying a given timestamp wins).
    t:
        Unix-second timestamp, which must lie within the track's time span.

    Raises
    ------
    ValueError
        If ``fixes`` is empty, or ``t`` falls outside ``[fixes[0][0],
        fixes[-1][0]]`` (this module interpolates; it does not extrapolate).
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes is empty; cannot estimate a position")

    t_first = _time_of(fixes[0])
    t_last = _time_of(fixes[-1])
    # Written as a positive test so a NaN t is rejected rather than slipping through.
    if not t_first <= t <= t_last:
        raise ValueError(
            f"t={t!r} is outside the track's time span [{t_first!r}, {t_last!r}]"
        )

    # First index whose timestamp is strictly greater than t. Because
    # t_first <= t <= t_last, idx is always in [1, n]; idx == n means t sits on
    # (or is tied with) the final fix.
    idx = bisect_right(fixes, t, key=_time_of)
    if idx >= n:
        _, lon, lat = fixes[-1]
        return (_wrap_lon(lon), float(lat))

    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]

    # t1 > t >= t0 by construction of bisect_right, so the span is non-zero.
    fraction = (t - t0) / (t1 - t0)
    if fraction <= 0.0:
        return (_wrap_lon(lon0), float(lat0))

    forward_azimuth, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    if not distance or not math.isfinite(forward_azimuth):
        # Coincident fixes: the azimuth is undefined and the ship has not moved.
        return (_wrap_lon(lon0), float(lat0))

    lon, lat, _ = _GEOD.fwd(lon0, lat0, forward_azimuth, fraction * distance)
    return (_wrap_lon(lon), float(lat))
```