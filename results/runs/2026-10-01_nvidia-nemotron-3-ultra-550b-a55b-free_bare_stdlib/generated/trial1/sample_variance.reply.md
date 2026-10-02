```python
def sample_variance(values):
    """
    Return the unbiased sample variance of the given values.

    Args:
        values: A sequence of floats (or ints).

    Returns:
        float: The sample variance, or None if fewer than two values are provided.
    """
    data = list(values)
    n = len(data)
    if n < 2:
        return None
    mean = sum(data) / n
    ss = sum((x - mean) ** 2 for x in data)
    return ss / (n - 1)
```