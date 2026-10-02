```python
from datetime import datetime
from zoneinfo import ZoneInfo

def elapsed_hours(start: str, end: str, tz_name: str) -> float:
    """
    Return the number of hours elapsed between two local wall-clock times in the given IANA time zone.

    Parameters
    ----------
    start: ISO 8601 local date-time string without offset (e.g., "2026-03-01T09:30:00").
    end:   ISO 8601 local date-time string without offset.
    tz_name: IANA time zone name (e.g., "America/New_York").

    Returns
    -------
    float: Elapsed hours (can be fractional, negative if end is before start).
    """
    tz = ZoneInfo(tz_name)
    dt_start = datetime.fromisoformat(start).replace(tzinfo=tz)
    dt_end = datetime.fromisoformat(end).replace(tzinfo=tz)
    delta = dt_end - dt_start
    return delta.total_seconds() / 3600.0
```