```python
def group_means(rows):
    """
    Compute the mean of values for each key, ignoring None values (SQL AVG semantics).

    Args:
        rows: An iterable of (key, value) pairs where key is a string and value is a float or None.

    Returns:
        A dictionary mapping each key to the mean of its non-None values, or None if all values are None.
    """
    sums = {}
    counts = {}
    keys_seen = set()

    for key, value in rows:
        keys_seen.add(key)
        if value is not None:
            sums[key] = sums.get(key, 0.0) + value
            counts[key] = counts.get(key, 0) + 1

    result = {}
    for key in keys_seen:
        count = counts.get(key, 0)
        if count > 0:
            result[key] = sums[key] / count
        else:
            result[key] = None

    return result
```