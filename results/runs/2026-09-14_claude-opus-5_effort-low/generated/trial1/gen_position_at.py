"""Estimate a ship's position at an arbitrary time from a track of GPS fixes.

Positions are interpolated *along the geodesic* between the two bracketing
fixes on the WGS84 ellipsoid, which keeps the result correct anywhere on the
ocean -- including across the antimeridian and at high latitudes, where naive
linear interpolation of longitude/latitude fails.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import List, Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

_GEOD = None


def _geod() -> Geod:
    """Return a lazily constructed WGS84 geodesic calculator."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def position_at(
    fixes: Sequence[Tuple[float, float, float]], t: float
) -> Tuple[float, float]:
    """Estimate the position at time ``t`` from chronologically sorted fixes.

    Args:
        fixes: Sequence of ``(timestamp, lon, lat)`` tuples, sorted by
            timestamp. Timestamps are Unix seconds; ``lon``/``lat`` are WGS84
            degrees.
        t: Unix timestamp, within the closed interval spanned by ``fixes``.

    Returns:
        ``(lon, lat)`` in WGS84 degrees, longitude normalized to [-180, 180).

    Raises:
        ValueError: If ``fixes`` is empty, is not sorted, or ``t`` lies
            outside the time span covered by ``fixes``.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    times: List[float] = [float(f[0]) for f in fixes]
    for a, b in zip(times, times[1:]):
        if b < a:
            raise ValueError("fixes must be sorted by ascending timestamp")

    t = float(t)
    if t < times[0] or t > times[-1]:
        raise ValueError(
            f"t={t!r} is outside the track span [{times[0]!r}, {times[-1]!r}]"
        )

    # Index of the first fix strictly after t; t is in range, so 0 < i <= n
    # unless t sits exactly on the last (or a repeated last) timestamp.
    i = bisect_right(times, t)
    if i == 0:  # t == times[0]
        return _normalize(float(fixes[0][1]), float(fixes[0][2]))
    if i == len(times):  # t == times[-1]
        return _normalize(float(fixes[-1][1]), float(fixes[-1][2]))

    t0, lon0, lat0 = (float(x) for x in fixes[i - 1][:3])
    t1, lon1, lat1 = (float(x) for x in fixes[i][:3])

    span = t1 - t0
    if span <= 0.0:
        # Duplicate timestamps: no motion can be inferred, take the earlier fix.
        return _normalize(lon0, lat0)

    frac = (t - t0) / span
    if frac <= 0.0:
        return _normalize(lon0, lat0)
    if frac >= 1.0:
        return _normalize(lon1, lat1)

    g = _geod()
    az12, _az21, dist = g.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return _normalize(lon0, lat0)

    lon, lat, _back_az = g.fwd(lon0, lat0, az12, dist * frac)
    return _normalize(lon, lat)


def _normalize(lon: float, lat: float) -> Tuple[float, float]:
    """Wrap longitude into [-180, 180) and clamp latitude to [-90, 90]."""
    lon = (lon + 180.0) % 360.0 - 180.0
    lat = max(-90.0, min(90.0, lat))
    return (lon, lat)