"""Estimate a ship's position between GPS fixes.

Positions are interpolated along the geodesic (shortest path on the WGS84
ellipsoid) joining the two bracketing fixes, at constant speed in time.  This
is what a vessel steaming between two reported positions actually approximates,
and unlike linear interpolation of lon/lat it stays correct at high latitudes,
across the antimeridian, and over long legs.

Importing this module has no side effects.
"""

from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 geodesic calculator (built on first use, then cached)."""
    return Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated ``(lon, lat)`` of the ship at time ``t``.

    Parameters
    ----------
    fixes:
        Chronologically sorted sequence of ``(timestamp, lon, lat)`` tuples.
        Timestamps are Unix seconds; ``lon``/``lat`` are WGS84 degrees.
    t:
        Unix timestamp, within ``[fixes[0][0], fixes[-1][0]]``.

    Returns
    -------
    (lon, lat) in WGS84 degrees, with longitude wrapped into [-180, 180).

    Raises
    ------
    ValueError
        If ``fixes`` is empty, is not sorted by timestamp, or ``t`` lies
        outside the covered interval.
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes is empty")

    times = [float(f[0]) for f in fixes]
    for i in range(1, n):
        if times[i] < times[i - 1]:
            raise ValueError("fixes must be sorted chronologically")

    t = float(t)
    if t < times[0] or t > times[-1]:
        raise ValueError(
            f"t={t!r} is outside the fix interval [{times[0]!r}, {times[-1]!r}]"
        )

    # Locate the leg [i, i+1] containing t.  bisect_right puts t after any run
    # of equal timestamps, so ties resolve to the last fix with that timestamp.
    j = bisect_right(times, t)
    if j == 0:  # t == times[0] and it is the only such value
        return _normalize_lon(float(fixes[0][1])), float(fixes[0][2])
    if j >= n:  # t is at (or numerically at) the final timestamp
        return _normalize_lon(float(fixes[-1][1])), float(fixes[-1][2])

    i = j - 1
    t0, lon0, lat0 = times[i], float(fixes[i][1]), float(fixes[i][2])
    t1, lon1, lat1 = times[j], float(fixes[j][1]), float(fixes[j][2])

    span = t1 - t0
    if span <= 0.0:  # duplicate timestamps: no elapsed time to interpolate over
        return _normalize_lon(lon0), lat0

    frac = (t - t0) / span
    if frac <= 0.0:
        return _normalize_lon(lon0), lat0
    if frac >= 1.0:
        return _normalize_lon(lon1), lat1

    geod = _geod()
    az12, _az21, dist = geod.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:  # ship stationary over this leg
        return _normalize_lon(lon0), lat0

    lon, lat, _back_az = geod.fwd(lon0, lat0, az12, dist * frac)
    return _normalize_lon(lon), lat