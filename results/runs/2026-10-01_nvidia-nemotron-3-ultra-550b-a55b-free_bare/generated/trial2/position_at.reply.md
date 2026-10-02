```python
import bisect
from pyproj import Geod

def position_at(fixes, t):
    """
    Estimate the ship's position at time `t` by geodesic interpolation between
    the two bracketing GPS fixes.

    Parameters
    ----------
    fixes : list of tuple
        Chronologically sorted list of (timestamp, longitude, latitude) tuples.
        Timestamps are Unix seconds; coordinates are WGS84 degrees.
    t : float
        Target timestamp (Unix seconds), guaranteed to lie between the first
        and last fix timestamps (inclusive).

    Returns
    -------
    tuple
        (longitude, latitude) in degrees at time `t`.
    """
    if not fixes:
        raise ValueError("fixes list is empty")

    timestamps = [fix[0] for fix in fixes]
    idx = bisect.bisect_left(timestamps, t)

    # Exact match
    if idx < len(fixes) and timestamps[idx] == t:
        return (fixes[idx][1], fixes[idx][2])

    # t is outside the range (should not happen per spec, but guard anyway)
    if idx == 0:
        raise ValueError("t is before the first fix")
    if idx == len(fixes):
        raise ValueError("t is after the last fix")

    # Interpolate between fixes[idx-1] and fixes[idx]
    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]
    fraction = (t - t0) / (t1 - t0)

    geod = Geod(ellps="WGS84")
    az12, _, dist = geod.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = geod.fwd(lon0, lat0, az12, dist * fraction)

    return (lon, lat)
```