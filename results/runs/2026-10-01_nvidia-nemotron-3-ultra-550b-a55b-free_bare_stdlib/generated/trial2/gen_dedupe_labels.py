def dedupe_labels(labels):
    """
    Remove duplicate labels case-insensitively while preserving order.

    Args:
        labels (list[str]): List of label strings.

    Returns:
        list[str]: New list containing the first occurrence of each label,
        with duplicates (ignoring case) removed.
    """
    seen = set()
    result = []
    for label in labels:
        lower = label.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(label)
    return result