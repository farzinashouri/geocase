```python
def sample_variance(values):
    """
    Compute the unbiased sample variance of a sequence of floats.

    Parameters
    ----------
    values : sequence of float
        The data points.

    Returns
    -------
    float or None
        The sample variance, or None if fewer than two values are provided.
    """
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    ss = sum((x - mean) ** 2 for x in values)
    return ss / (n - 1)
```