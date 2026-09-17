```python
"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Interpolation is done along the WGS84 geodesic between the two fixes that
bracket the requested time, so results are correct across the antimeridian,
near the poles, and over long legs where straight-line lon/lat interpolation
would drift off the true track.
"""

from bisect import bisect_right

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Return the estimated (lon, lat) of the ship at Unix time ``t``.

    Parameters
    ----------
    fixes : sequence of (timestamp, lon, lat)
        Chronologically sorted GPS fixes. Timestamps are Unix seconds,
        positions are WGS84 degrees.
    t : float
        Timestamp to evaluate, between the first and last fix (inclusive).

    Returns
    -------
    (lon, lat) : tuple of float
        Interpolated position in WGS84 degrees, longitude in [-180, 180].

    Raises
    ------
    ValueError
        If ``fixes`` is empty or ``t`` lies outside the covered interval.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    times = [f[0] for f in fixes]
    if not (times[0] <= t <= times[-1]):
        raise ValueError(
            f"t={t} is outside the fix interval [{times[0]}, {times[-1]}]"
        )

    # Index of the last fix whose timestamp is <= t.
    i = bisect_right(times, t) - 1
    t0, lon0, lat0 = fixes[i]

    # Exact hit on a fix, or t equals the final timestamp.
    if t == t0 or i == len(fixes) - 1:
        return (float(lon0), float(lat0))

    t1, lon1, lat1 = fixes[i + 1]

    # Duplicate timestamps: no elapsed time, so no motion to interpolate.
    if t1 == t0:
        return (float(lon0), float(lat0))

    frac = (t - t0) / (t1 - t0)

    # Geodesic from fix i to fix i+1: forward azimuth and distance in metres.
    az, _back_az, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return (float(lon0), float(lat0))

    # Advance the proportional distance along that geodesic.
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az, dist * frac)
    return (float(lon), float(lat))
```