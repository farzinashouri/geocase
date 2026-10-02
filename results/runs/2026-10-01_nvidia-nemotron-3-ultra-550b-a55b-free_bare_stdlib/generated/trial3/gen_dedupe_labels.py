def dedupe_labels(labels):
    """Return a new list with duplicates removed case-insensitively, preserving order and first occurrence."""
    seen = set()
    result = []
    for label in labels:
        lower = label.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(label)
    return result