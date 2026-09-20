"""Estimate a ship's position at an arbitrary time from a track of GPS fixes.

Positions are interpolated along the geodesic (shortest path on the WGS84
ellipsoid) between the two bracketing fixes, which is the right model for a
vessel steering a great-circle-ish course at sea. Doing the interpolation in
geodesic space -- rather than linearly in lon/lat -- keeps the result correct
at high latitudes, across the antimeridian, and near the poles, where naive
component-wise blending of degrees is badly wrong.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import List, Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_GEOD: Geod | None = None


def _geod() -> Geod:
    """Return a lazily constructed WGS84 Geod (keeps import side-effect free)."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Estimate the ship's position at time ``t``.

    Args:
        fixes: chronologically sorted ``(timestamp, lon, lat)`` tuples.
            Timestamps are Unix seconds; ``lon``/``lat`` are WGS84 degrees.
            Repeated timestamps are allowed; the last fix of a repeated
            timestamp wins.
        t: Unix-second timestamp, within ``[fixes[0][0], fixes[-1][0]]``.

    Returns:
        ``(lon, lat)`` in WGS84 degrees, with longitude in [-180, 180).

    Raises:
        ValueError: if ``fixes`` is empty, is not sorted by timestamp, or
            ``t`` lies outside the track's time span.
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

    # Index of the first fix strictly after t; the bracketing pair is (i-1, i).
    i = bisect_right(times, t)
    if i == 0:  # t == times[0], possibly with duplicates at the start
        i = 1
    if i >= len(times):  # t == times[-1]
        _, lon, lat = fixes[-1]
        return (_normalize_lon(float(lon)), float(lat))

    t0, lon0, lat0 = times[i - 1], float(fixes[i - 1][1]), float(fixes[i - 1][2])
    t1, lon1, lat1 = times[i], float(fixes[i][1]), float(fixes[i][2])

    span = t1 - t0
    if span <= 0.0:
        # Duplicate timestamps: no elapsed time to interpolate over.
        return (_normalize_lon(lon1), lat1)

    frac = (t - t0) / span
    if frac <= 0.0:
        return (_normalize_lon(lon0), lat0)
    if frac >= 1.0:
        return (_normalize_lon(lon1), lat1)

    g = _geod()
    az, _back_az, dist = g.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        # Stationary between the two fixes; azimuth is undefined.
        return (_normalize_lon(lon0), lat0)

    lon, lat, _ = g.fwd(lon0, lat0, az, dist * frac)
    return (_normalize_lon(lon), lat)