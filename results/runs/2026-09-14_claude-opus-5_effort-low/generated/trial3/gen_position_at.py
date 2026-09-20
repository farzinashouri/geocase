"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions are interpolated along the great circle between the two bracketing
fixes (spherical linear interpolation on unit vectors), so results are correct
near the poles and across the antimeridian, where naive lon/lat interpolation
breaks down.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from typing import Sequence, Tuple

__all__ = ["position_at"]

Fix = Tuple[float, float, float]


def _to_vector(lon_deg: float, lat_deg: float) -> Tuple[float, float, float]:
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    cos_lat = math.cos(lat)
    return (cos_lat * math.cos(lon), cos_lat * math.sin(lon), math.sin(lat))


def _to_lonlat(x: float, y: float, z: float) -> Tuple[float, float]:
    lon = math.degrees(math.atan2(y, x))
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    # Normalise to (-180, 180]; atan2 can return exactly -180 for due-west points.
    if lon <= -180.0:
        lon += 360.0
    return (lon, lat)


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated ``(lon, lat)`` of the ship at time ``t``.

    ``fixes`` is a chronologically sorted sequence of ``(timestamp, lon, lat)``
    WGS84 fixes with Unix-second timestamps, and ``t`` must lie within the time
    span they cover. Interpolation is done along the great circle joining the
    two surrounding fixes, at constant speed in time.
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes is empty")
    if n == 1:
        ts, lon, lat = fixes[0]
        if t != ts:
            raise ValueError("t is outside the range covered by fixes")
        return (float(lon), float(lat))

    times = [float(f[0]) for f in fixes]
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("fixes must be sorted chronologically")

    t = float(t)
    if t < times[0] or t > times[-1]:
        raise ValueError("t is outside the range covered by fixes")

    # Index of the first fix strictly after t; the pair (i-1, i) brackets t.
    i = bisect_right(times, t)
    if i == 0:  # t == times[0] and times[0] is not duplicated below it
        i = 1
    elif i == n:  # t at or past the final timestamp
        i = n - 1
        # Walk back over any fixes sharing the final timestamp.
        while i > 1 and times[i - 1] == times[i]:
            i -= 1
    i = max(i, 1)

    t0, lon0, lat0 = times[i - 1], float(fixes[i - 1][1]), float(fixes[i - 1][2])
    t1, lon1, lat1 = times[i], float(fixes[i][1]), float(fixes[i][2])

    dt = t1 - t0
    if dt <= 0.0:
        # Duplicate timestamps: nothing to interpolate over, take the later fix.
        return (lon1, lat1)

    f = (t - t0) / dt
    if f <= 0.0:
        return (lon0, lat0)
    if f >= 1.0:
        return (lon1, lat1)

    v0 = _to_vector(lon0, lat0)
    v1 = _to_vector(lon1, lat1)

    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(v0, v1))))
    omega = math.acos(dot)

    if omega < 1e-10:
        # Effectively the same point (or a sub-millimetre separation): linear
        # blending is numerically safer than dividing by sin(omega) here.
        x, y, z = (a + f * (b - a) for a, b in zip(v0, v1))
    else:
        # Near-antipodal fixes have no unique great circle; slerp still returns
        # a point on one of them, which is the best available answer.
        sin_omega = math.sin(omega)
        s0 = math.sin((1.0 - f) * omega) / sin_omega
        s1 = math.sin(f * omega) / sin_omega
        x, y, z = (s0 * a + s1 * b for a, b in zip(v0, v1))

    norm = math.sqrt(x * x + y * y + z * z)
    if norm == 0.0:
        return (lon0, lat0)
    return _to_lonlat(x / norm, y / norm, z / norm)