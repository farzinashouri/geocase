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
    for key, value in rows:
        if key not in sums:
            sums[key] = 0.0
            counts[key] = 0
        if value is not None:
            sums[key] += value
            counts[key] += 1

    result = {}
    for key in sums:
        if counts[key] > 0:
            result[key] = sums[key] / counts[key]
        else:
            result[key] = None
    return result
```