def dedupe_labels(labels):
    """
    Return a new list with duplicates removed case-insensitively.
    The first occurrence of each label (preserving original case) is kept,
    and the original order is maintained.
    """
    seen = set()
    result = []
    for label in labels:
        lower = label.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(label)
    return result