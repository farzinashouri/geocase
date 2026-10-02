```python
def sample_variance(values):
    """
    Return the unbiased sample variance of the given sequence of floats.
    If fewer than two values are provided, return None.
    """
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    ssd = sum((x - mean) ** 2 for x in values)
    return ssd / (n - 1)
```