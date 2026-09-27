```python
"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions between two consecutive fixes are interpolated along the geodesic
(shortest path on the WGS84 ellipsoid) at constant speed, which is accurate
anywhere on the ocean and behaves correctly across the antimeridian and near
the poles where naive linear interpolation of lon/lat fails.
"""

from bisect import bisect_right

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Return the estimated (lon, lat) of the ship at time ``t``.

    Parameters
    ----------
    fixes : list of (timestamp, lon, lat)
        Chronologically sorted GPS fixes. Timestamps are Unix seconds,
        positions are WGS84 degrees.
    t : float
        A timestamp within [fixes[0][0], fixes[-1][0]].

    Returns
    -------
    (lon, lat) : tuple of float
    """
    if not fixes:
        raise ValueError("fixes must be non-empty")

    times = [f[0] for f in fixes]
    t0, t1 = times[0], times[-1]
    if t < t0 or t > t1:
        raise ValueError("t must lie within the range of the fixes")

    # Exact boundary hits (and the single-fix case).
    if t == t0:
        return (fixes[0][1], fixes[0][2])
    if t == t1:
        return (fixes[-1][1], fixes[-1][2])

    # Locate the interval [i-1, i] that brackets t.
    i = bisect_right(times, t)
    # bisect_right gives the first index with times[index] > t; since
    # t0 < t < t1 this is in [1, len-1].
    lo = i - 1
    hi = i

    ts_lo, lon_lo, lat_lo = fixes[lo]
    ts_hi, lon_hi, lat_hi = fixes[hi]

    span = ts_hi - ts_lo
    if span <= 0:
        # Duplicate/zero-width timestamp; fall back to the earlier fix.
        return (lon_lo, lat_lo)

    frac = (t - ts_lo) / span
    if frac <= 0.0:
        return (lon_lo, lat_lo)
    if frac >= 1.0:
        return (lon_hi, lat_hi)

    # Interpolate along the geodesic between the two bracketing fixes.
    fwd_az, _, dist = _GEOD.inv(lon_lo, lat_lo, lon_hi, lat_hi)
    if dist == 0.0:
        return (lon_lo, lat_lo)

    lon, lat, _ = _GEOD.fwd(lon_lo, lat_lo, fwd_az, dist * frac)
    return (lon, lat)
```