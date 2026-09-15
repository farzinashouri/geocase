"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions are interpolated along the geodesic (shortest path on the WGS84
ellipsoid) between the two bracketing fixes, assuming constant speed over the
segment. This is correct anywhere on the globe: it crosses the antimeridian
without wrapping artifacts and behaves sensibly at high latitudes, both of
which naive linear interpolation of lon/lat gets wrong.

Importing this module has no side effects.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import List, Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

_GEOD = None


def _geod() -> Geod:
    """Return the shared WGS84 geodesic calculator, building it on first use."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def _wrap_lon(lon: float) -> float:
    """Normalize a longitude to [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def position_at(
    fixes: Sequence[Tuple[float, float, float]], t: float
) -> Tuple[float, float]:
    """Estimate the position at time ``t`` from chronologically sorted fixes.

    Args:
        fixes: Sequence of ``(timestamp, lon, lat)`` tuples, sorted by
            timestamp ascending. Timestamps are Unix seconds; ``lon``/``lat``
            are WGS84 degrees.
        t: Unix timestamp, within ``[fixes[0][0], fixes[-1][0]]``.

    Returns:
        ``(lon, lat)`` in WGS84 degrees, with longitude in [-180, 180).

    Raises:
        ValueError: If ``fixes`` is empty, not sorted by timestamp, or ``t``
            lies outside the covered interval.
    """
    pts: List[Tuple[float, float, float]] = [
        (float(ts), float(lon), float(lat)) for ts, lon, lat in fixes
    ]
    if not pts:
        raise ValueError("fixes must contain at least one fix")

    times = [p[0] for p in pts]
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("fixes must be sorted by ascending timestamp")

    t = float(t)
    if t < times[0] or t > times[-1]:
        raise ValueError(
            f"t={t!r} is outside the fix interval [{times[0]!r}, {times[-1]!r}]"
        )

    # Rightmost segment whose start is at or before t.
    i = bisect_right(times, t) - 1
    if i < 0:
        i = 0
    if i >= len(pts) - 1:
        # t equals the final timestamp (or duplicates of it).
        _, lon, lat = pts[-1]
        return (_wrap_lon(lon), lat)

    t0, lon0, lat0 = pts[i]
    t1, lon1, lat1 = pts[i + 1]

    span = t1 - t0
    if span <= 0.0:
        # Duplicate timestamps: no elapsed time to interpolate over.
        return (_wrap_lon(lon0), lat0)

    frac = (t - t0) / span
    if frac <= 0.0:
        return (_wrap_lon(lon0), lat0)
    if frac >= 1.0:
        return (_wrap_lon(lon1), lat1)

    g = _geod()
    az12, _az21, dist = g.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        # Stationary segment; azimuth is undefined but irrelevant.
        return (_wrap_lon(lon0), lat0)

    lon, lat, _back_az = g.fwd(lon0, lat0, az12, dist * frac)
    return (_wrap_lon(lon), lat)