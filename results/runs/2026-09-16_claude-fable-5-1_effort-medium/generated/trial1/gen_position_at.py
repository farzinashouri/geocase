"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

The position is obtained by geodesic (great-circle) interpolation on the
WGS84 ellipsoid between the two fixes that bracket the requested time.
Working in geodesic terms rather than on raw lon/lat values keeps the
result correct across the antimeridian and near the poles.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Sequence, Tuple

from pyproj import Geod

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_WGS84 = Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into the range [-180, 180]."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated (lon, lat) of the ship at time ``t``.

    Parameters
    ----------
    fixes:
        Chronologically sorted sequence of ``(timestamp, lon, lat)`` fixes.
        Timestamps are Unix seconds; positions are WGS84 degrees.
    t:
        Unix timestamp between the first and last fix (inclusive).

    Raises
    ------
    ValueError
        If ``fixes`` is empty or ``t`` is outside the covered time range.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    first_t = fixes[0][0]
    last_t = fixes[-1][0]
    if t < first_t or t > last_t:
        raise ValueError(
            f"t={t} is outside the fix range [{first_t}, {last_t}]"
        )

    timestamps = [f[0] for f in fixes]

    # Index of the first fix strictly after t.
    hi = bisect_right(timestamps, t)
    lo = hi - 1

    # t coincides with the last fix (or a run of fixes sharing that time).
    if hi >= len(fixes):
        _, lon, lat = fixes[-1]
        return _normalize_lon(lon), lat

    t0, lon0, lat0 = fixes[lo]
    t1, lon1, lat1 = fixes[hi]

    # Exact hit on a fix, or degenerate zero-duration segment.
    if t == t0 or t1 == t0:
        return _normalize_lon(lon0), lat0

    frac = (t - t0) / (t1 - t0)

    # Great-circle interpolation on the WGS84 ellipsoid.
    fwd_az, _, dist = _WGS84.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return _normalize_lon(lon0), lat0

    lon, lat, _ = _WGS84.fwd(lon0, lat0, fwd_az, dist * frac)
    return _normalize_lon(lon), lat