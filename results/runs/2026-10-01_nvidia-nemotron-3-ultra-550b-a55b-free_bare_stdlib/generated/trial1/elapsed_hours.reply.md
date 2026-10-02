```python
from datetime import datetime
from zoneinfo import ZoneInfo

def elapsed_hours(start: str, end: str, tz_name: str) -> float:
    """
    Calculate the actual elapsed hours between two local wall-clock times in a given IANA time zone.

    Args:
        start: ISO 8601 local date-time string without offset (e.g., "2026-03-01T09:30:00").
        end:   ISO 8601 local date-time string without offset.
        tz_name: IANA time zone name (e.g., "America/New_York").

    Returns:
        The number of hours (as a float) that actually elapse between the two instants.
        The result may be negative if `end` is earlier than `start`.
    """
    # Parse naive datetime objects from the ISO strings.
    start_naive = datetime.fromisoformat(start)
    end_naive = datetime.fromisoformat(end)

    # Attach the time zone to interpret them as wall-clock times in that zone.
    tz = ZoneInfo(tz_name)
    start_aware = start_naive.replace(tzinfo=tz)
    end_aware = end_naive.replace(tzinfo=tz)

    # Compute the difference (accounts for DST transitions automatically).
    delta = end_aware - start_aware

    # Convert to hours.
    return delta.total_seconds() / 3600.0
```