import bisect
from pyproj import Geod

# Geodesic object for WGS84 ellipsoid
_geod = Geod(ellps="WGS84")

def position_at(fixes, t):
    """
    Estimate the ship's position at a given timestamp by linear interpolation
    along the great‑circle path between the two surrounding GPS fixes.

    Parameters
    ----------
    fixes : list of (int, float, float)
        Chronologically sorted list of (timestamp, lon, lat) tuples.
        Timestamps are Unix seconds, lon/lat are in degrees.
    t : int
        Timestamp between the first and last fix.

    Returns
    -------
    tuple
        (lon, lat) of the interpolated position in degrees.
    """
    if not fixes:
        raise ValueError("fixes list must not be empty")

    # Extract timestamps for binary search
    times = [f[0] for f in fixes]

    # Find rightmost index where times[idx] <= t
    idx = bisect.bisect_right(times, t) - 1

    # Clamp index to valid range
    if idx < 0:
        idx = 0
    if idx >= len(fixes) - 1:
        idx = len(fixes) - 2

    t0, lon0, lat0 = fixes[idx]
    t1, lon1, lat1 = fixes[idx + 1]

    # If t matches a fix exactly, return that position
    if t == t0:
        return (lon0, lat0)
    if t == t1:
        return (lon1, lat1)

    # Fraction of time elapsed between the two fixes
    frac = (t - t0) / (t1 - t0)

    # Compute azimuth and distance between the two fixes
    az12, az21, dist = _geod.inv(lon0, lat0, lon1, lat1)

    # Interpolate along the geodesic
    lon, lat, _ = _geod.fwd(lon0, lat0, az12, dist * frac)

    return (lon, lat)