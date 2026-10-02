```python
"""
Module for interpolating a ship's position at a given time from GPS fixes.

Uses geodesic (great-circle) interpolation on the WGS84 ellipsoid via pyproj.
"""

from __future__ import annotations
import bisect
from typing import List, Tuple

try:
    from pyproj import Geod
except ImportError as e:
    raise ImportError("pyproj is required for geodesic interpolation") from e

# Pre-create a Geod object for WGS84 to avoid repeated instantiation.
_GEOD = Geod(ellps="WGS84")


def position_at(fixes: List[Tuple[float, float, float]], t: float) -> Tuple[float, float]:
    """
    Estimate the ship's position at timestamp `t` by linear interpolation along the geodesic
    between the two bracketing GPS fixes.

    Parameters
    ----------
    fixes : list of (timestamp, longitude, latitude)
        Chronologically sorted GPS fixes. Timestamps are Unix seconds (float).
        Longitudes and latitudes are in degrees (WGS84).
    t : float
        Target timestamp (Unix seconds). Must lie between the first and last fix (inclusive).

    Returns
    -------
    (longitude, latitude) : tuple of float
        Estimated position in degrees (WGS84).
    """
    if not fixes:
        raise ValueError("fixes list must not be empty")

    # Extract timestamps for binary search
    timestamps = [fix[0] for fix in fixes]

    # Find the index of the fix immediately before or at t
    idx = bisect.bisect_right(timestamps, t) - 1

    # If t is exactly at a fix, return that fix directly
    if idx >= 0 and timestamps[idx] == t:
        _, lon, lat = fixes[idx]
        return (lon, lat)

    # If t is before the first fix or after the last fix, clamp to the nearest fix
    # (The problem states t is between first and last, but we handle gracefully.)
    if idx < 0:
        _, lon, lat = fixes[0]
        return (lon, lat)
    if idx >= len(fixes) - 1:
        _, lon, lat = fixes[-1]
        return (lon, lat)

    # Bracketing fixes
    t0, lon0, lat0 = fixes[idx]
    t1, lon1, lat1 = fixes[idx + 1]

    # Time fraction between the two fixes
    frac = (t - t0) / (t1 - t0)

    # Create a geodesic line between the two points
    line = _GEOD.line(lon0, lat0, lon1, lat1)

    # Distance along the geodesic at the given fraction
    target_dist = frac * line.s13

    # Compute the position at that distance
    lon, lat, _ = line.position(target_dist)

    return (lon, lat)


# Example usage (not executed on import)
if __name__ == "__main__":
    # Simple test: two fixes 1 hour apart, interpolate at half hour
    test_fixes = [
        (0.0, -122.0, 37.0),      # San Francisco
        (3600.0, -120.0, 38.0),   # Somewhere east-northeast
    ]
    print(position_at(test_fixes, 1800.0))
```