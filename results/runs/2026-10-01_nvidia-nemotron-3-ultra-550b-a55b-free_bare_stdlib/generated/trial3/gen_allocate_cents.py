import math

def allocate_cents(total, weights):
    """
    Allocate `total` cents proportionally to `weights`.

    Args:
        total (int): Non-negative integer number of cents to allocate.
        weights (list[float]): List of positive numbers representing weights.

    Returns:
        list[int]: List of integer cents allocated to each weight, summing to `total`.
                   Each allocation is within 1 cent of its exact proportional share.
    """
    n = len(weights)
    if total == 0:
        return [0] * n

    sum_weights = sum(weights)
    # Exact proportional shares (as floats)
    exact = [total * w / sum_weights for w in weights]
    # Floor of each exact share
    floors = [int(math.floor(x)) for x in exact]
    # Fractional remainders
    remainders = [x - f for x, f in zip(exact, floors)]

    remaining = total - sum(floors)
    # Indices sorted by remainder descending, then by index ascending for deterministic tie-breaking
    indices = sorted(range(n), key=lambda i: (-remainders[i], i))

    # Distribute the remaining cents to the largest remainders
    for i in indices[:remaining]:
        floors[i] += 1

    return floors