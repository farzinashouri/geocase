```python
from fractions import Fraction

def allocate_cents(total, weights):
    """
    Allocate `total` cents proportionally to `weights`.

    Args:
        total: Non-negative integer number of cents.
        weights: List of positive numbers (int, float, etc.).

    Returns:
        List of integers of same length as `weights`, summing to `total`.
        Each share is within one cent of its exact proportional value.
    """
    if total == 0:
        return [0] * len(weights)
    if not weights:
        return []

    # Convert weights to Fractions for exact arithmetic
    frac_weights = [Fraction(w) for w in weights]
    sum_weights = sum(frac_weights)

    # Exact shares as Fractions
    exact_shares = [total * w / sum_weights for w in frac_weights]

    # Floor of each exact share
    floors = [int(s) for s in exact_shares]  # int() truncates toward zero; shares are non-negative so this is floor
    allocated = floors[:]
    remainder = total - sum(floors)

    # Fractional parts for remainder distribution
    # Each element: (fractional_part, index)
    fractional_parts = [(exact_shares[i] - floors[i], i) for i in range(len(weights))]

    # Sort by fractional part descending, then by index ascending for tie-breaking
    fractional_parts.sort(key=lambda x: (-x[0], x[1]))

    # Distribute the remaining cents
    for i in range(remainder):
        idx = fractional_parts[i][1]
        allocated[idx] += 1

    return allocated

if __name__ == "__main__":
    # Simple self-test
    print(allocate_cents(100, [1, 1, 1]))          # e.g. [34, 33, 33]
    print(allocate_cents(10, [3, 2]))              # [6, 4]
    print(allocate_cents(5, [0.1, 0.2, 0.7]))      # [1, 1, 3]
    print(allocate_cents(0, [1, 2, 3]))            # [0, 0, 0]
```