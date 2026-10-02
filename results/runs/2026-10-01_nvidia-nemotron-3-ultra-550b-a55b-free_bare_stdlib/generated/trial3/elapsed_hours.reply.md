```python
from datetime import datetime
from zoneinfo import ZoneInfo

def elapsed_hours(start: str, end: str, tz_name: str) -> float:
    """
    Return the number of hours that actually elapse between two local wall-clock times
    in the given IANA time zone.

    Args:
        start: ISO 8601 local date-time string without offset (e.g. "2026-03-01T09:30:00").
        end:   ISO 8601 local date-time string without offset.
        tz_name: IANA time zone name (e.g. "America/New_York").

    Returns:
        Elapsed time in hours as a float.
    """
    tz = ZoneInfo(tz_name)
    start_dt = datetime.fromisoformat(start).replace(tzinfo=tz)
    end_dt = datetime.fromisoformat(end).replace(tzinfo=tz)
    delta = end_dt - start_dt
    return delta.total_seconds() / 3600.0
```