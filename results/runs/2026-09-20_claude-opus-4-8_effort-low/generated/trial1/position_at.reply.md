```python
"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions are interpolated along the geodesic (shortest path on the WGS84
ellipsoid) between the two bracketing fixes, with fraction proportional to
elapsed time. Geodesic interpolation keeps results accurate anywhere on the
ocean, including across the antimeridian and at high latitudes, where naive
linear interpolation of lon/lat degrees would be wrong.
"""

from bisect import bisect_right

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Return the estimated (lon, lat) of the ship at time ``t``.

    ``fixes`` is a chronologically sorted list of ``(timestamp, lon, lat)``
    tuples (Unix seconds, WGS84 degrees). ``t`` must lie within the time span
    covered by ``fixes``.
    """
    if not fixes:
        raise ValueError("fixes must be non-empty")

    times = [f[0] for f in fixes]
    if t < times[0] or t > times[-1]:
        raise ValueError("t is outside the range of fixes")

    # Exact hit or first fix.
    if t == times[0]:
        return (fixes[0][1], fixes[0][2])
    if t == times[-1]:
        return (fixes[-1][1], fixes[-1][2])

    # Find the fix just after t; the bracketing segment is [i-1, i].
    i = bisect_right(times, t)
    t0, lon0, lat0 = fixes[i - 1]
    t1, lon1, lat1 = fixes[i]

    if t == t0:
        return (lon0, lat0)

    # Guard against duplicate/zero-duration timestamps.
    dt = t1 - t0
    if dt <= 0:
        return (lon1, lat1)

    frac = (t - t0) / dt

    # Geodesic inverse then forward: walk `frac` of the way along the
    # shortest ellipsoidal path from fix0 toward fix1.
    az_fwd, _az_back, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return (lon0, lat0)

    lon, lat, _back_az = _GEOD.fwd(lon0, lat0, az_fwd, dist * frac)
    return (lon, lat)
```