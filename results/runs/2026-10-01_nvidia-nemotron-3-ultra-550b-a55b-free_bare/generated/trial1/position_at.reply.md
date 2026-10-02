```python
import bisect
from pyproj import Geod

# Geodetic calculator for WGS84 ellipsoid
_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """
    Estimate the ship's position at time `t` by linear interpolation along the
    geodesic (great-circle) between the two surrounding GPS fixes.

    Parameters
    ----------
    fixes : list of (timestamp, lon, lat)
        Chronologically sorted GPS fixes. Timestamps are Unix seconds (float or int).
        Longitudes and latitudes are in decimal degrees (WGS84).
    t : float or int
        Target timestamp, guaranteed to lie between the first and last fix.

    Returns
    -------
    (lon, lat) : tuple of float
        Interpolated longitude and latitude in decimal degrees (WGS84).
    """
    # Extract timestamps for binary search
    timestamps = [fix[0] for fix in fixes]

    # Locate the interval [i-1, i] that contains t
    i = bisect.bisect_left(timestamps, t)

    # Exact match to an existing fix
    if i < len(fixes) and timestamps[i] == t:
        return (fixes[i][1], fixes[i][2])

    # t is strictly between fixes[i-1] and fixes[i]
    t1, lon1, lat1 = fixes[i - 1]
    t2, lon2, lat2 = fixes[i]

    # Guard against duplicate timestamps (should not occur in valid data)
    if t1 == t2:
        return (lon1, lat1)

    # Fraction of time elapsed between the two fixes
    frac = (t - t1) / (t2 - t1)

    # Geodesic distance and forward azimuth from fix1 to fix2
    az12, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)

    # Point at the interpolated distance along the geodesic
    lon, lat, _ = _GEOD.fwd(lon1, lat1, az12, frac * dist)

    return (lon, lat)
```