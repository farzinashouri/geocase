import pyproj
from typing import List, Tuple

# WGS84 geodetic calculator
_GEOD = pyproj.Geod(ellps="WGS84")

def position_at(fixes: List[Tuple[float, float, float]], t: float) -> Tuple[float, float]:
    """
    Estimate the ship's position at time `t` by linear interpolation along geodesics.

    Parameters
    ----------
    fixes : list of (timestamp, longitude, latitude)
        Chronologically sorted GPS fixes (Unix seconds, WGS84 degrees).
    t : float
        Target timestamp (Unix seconds), guaranteed to be between the first and last fix.

    Returns
    -------
    (longitude, latitude) : tuple of float
        Interpolated position in WGS84 degrees.
    """
    # Handle exact matches quickly
    for fix in fixes:
        if fix[0] == t:
            return (fix[1], fix[2])

    # Find the segment containing t
    for i in range(len(fixes) - 1):
        t1, lon1, lat1 = fixes[i]
        t2, lon2, lat2 = fixes[i + 1]
        if t1 <= t <= t2:
            # Fraction of time along the segment
            frac = (t - t1) / (t2 - t1)
            # Geodesic interpolation
            az12, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
            lon, lat, _ = _GEOD.fwd(lon1, lat1, az12, frac * dist)
            return (lon, lat)

    # Should never reach here if t is within bounds
    raise ValueError("Timestamp t is outside the range of fixes")