"""Estimate a ship's position between GPS fixes.

Positions are interpolated along the *geodesic* (the shortest path on the
WGS84 ellipsoid) between the two bracketing fixes, at constant speed in time.

Why not linear interpolation of (lon, lat)?  Because it is wrong exactly where
ships actually sail:

  * Antimeridian: interpolating between lon=179.9 and lon=-179.9 linearly
    sweeps the long way around the globe (~40000 km instead of ~20 km).
  * High latitudes: a degree of longitude shrinks with cos(lat), so a lon/lat
    average drifts off the true track -- tens of km on a long North Atlantic
    or Southern Ocean leg, and the error grows towards the poles.
  * Meridian convergence near the poles makes the lon/lat midpoint of two
    nearby fixes meaningless.

Geodesic interpolation via pyproj's Geod (inverse solution for the azimuth and
distance, forward solution for the intermediate point) has none of those
failure modes and is accurate to well under a metre anywhere on Earth.
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_geod: Geod | None = None


def _get_geod() -> Geod:
    """Return the shared WGS84 Geod, building it on first use.

    Built lazily so that importing this module has no side effects.
    """
    global _geod
    if _geod is None:
        _geod = Geod(ellps="WGS84")
    return _geod


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _find_segment(fixes: Sequence[Fix], t: float) -> int:
    """Index of the last fix whose timestamp is <= t.

    Plain binary search rather than bisect(key=...) so the function works on
    any sequence of fixes without allocating a parallel list of timestamps.
    Assumes `fixes` is sorted by timestamp, as documented.
    """
    lo, hi = 0, len(fixes) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fixes[mid][0] <= t:
            lo = mid
        else:
            hi = mid - 1
    return lo


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Estimate the ship's position at time `t`.

    Parameters
    ----------
    fixes:
        Chronologically sorted sequence of ``(timestamp, lon, lat)`` GPS fixes.
        Timestamps are Unix seconds; ``lon``/``lat`` are WGS84 degrees.
        Repeated timestamps are allowed; the last fix with a given timestamp
        wins.
    t:
        Unix timestamp, within ``[fixes[0][0], fixes[-1][0]]``.

    Returns
    -------
    ``(lon, lat)`` in WGS84 degrees, with longitude wrapped into [-180, 180).

    Raises
    ------
    ValueError
        If `fixes` is empty, if `t` is not finite, or if `t` falls outside the
        span of the fixes (this function interpolates; it does not extrapolate,
        because dead reckoning past the last fix is a different and much less
        trustworthy estimate).
    """
    if len(fixes) == 0:
        raise ValueError("fixes must contain at least one fix")

    t = float(t)
    if not math.isfinite(t):
        raise ValueError("t must be a finite timestamp")

    t_start = float(fixes[0][0])
    t_end = float(fixes[-1][0])
    if t < t_start or t > t_end:
        raise ValueError(
            f"t={t!r} is outside the fix span [{t_start!r}, {t_end!r}]"
        )

    i = _find_segment(fixes, t)

    t0, lon0, lat0 = (float(v) for v in fixes[i][:3])

    # Exact hit on a fix, or the final fix: report it as measured rather than
    # letting round-off move it.
    if t == t0 or i == len(fixes) - 1:
        return (_normalize_lon(lon0), float(lat0))

    t1, lon1, lat1 = (float(v) for v in fixes[i + 1][:3])

    # _find_segment guarantees t0 <= t < t1, so the span is strictly positive.
    frac = (t - t0) / (t1 - t0)

    geod = _get_geod()
    az12, _, dist = geod.inv(lon0, lat0, lon1, lat1)

    if dist == 0.0 or not math.isfinite(dist):
        # Ship stationary between the two fixes (or a degenerate/antipodal
        # inverse solution): the earlier fix is the best available estimate.
        return (_normalize_lon(lon0), lat0)

    lon, lat, _ = geod.fwd(lon0, lat0, az12, dist * frac)
    return (_normalize_lon(lon), lat)