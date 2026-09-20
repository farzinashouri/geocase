"""Estimate a ship's position at an arbitrary time from a track of GPS fixes.

Positions are interpolated along the WGS84 geodesic between the two fixes
that bracket the requested time, so results stay accurate across the
antimeridian, near the poles, and over long legs where a straight
lon/lat interpolation would drift off the great-circle track.
"""

from bisect import bisect_right
from typing import Sequence, Tuple

from pyproj import Geod

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_GEOD = Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180]."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated (lon, lat) of the ship at time ``t``.

    ``fixes`` must be sorted by timestamp and contain at least one fix.
    ``t`` must lie within [first timestamp, last timestamp].
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    times = [f[0] for f in fixes]
    if t < times[0] or t > times[-1]:
        raise ValueError(
            f"t={t} is outside the track span [{times[0]}, {times[-1]}]"
        )

    # Index of the first fix strictly after t. Fixes before it have ts <= t.
    hi = bisect_right(times, t)
    lo = hi - 1

    if hi >= len(fixes):
        # t equals the final timestamp (possibly a run of equal timestamps).
        _, lon, lat = fixes[-1]
        return (_normalize_lon(lon), lat)

    t0, lon0, lat0 = fixes[lo]
    t1, lon1, lat1 = fixes[hi]

    if t == t0:
        return (_normalize_lon(lon0), lat0)

    span = t1 - t0
    if span <= 0:
        return (_normalize_lon(lon0), lat0)

    frac = (t - t0) / span

    # Solve the inverse geodesic for the leg, then walk the fraction of it.
    fwd_az, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return (_normalize_lon(lon0), lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, fwd_az, dist * frac)
    return (_normalize_lon(lon), lat)