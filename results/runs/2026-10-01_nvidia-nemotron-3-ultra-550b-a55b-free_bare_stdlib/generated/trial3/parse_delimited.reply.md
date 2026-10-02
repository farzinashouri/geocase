```python
def parse_delimited(line: str) -> list[str]:
    """
    Parse a single CSV line according to RFC 4180.

    Args:
        line: A string containing one record (no trailing newline).

    Returns:
        A list of field strings. Empty fields are preserved.
    """
    fields = []
    field = []
    in_quotes = False
    i = 0
    n = len(line)

    while i < n:
        ch = line[i]
        if in_quotes:
            if ch == '"':
                # Look ahead for escaped quote
                if i + 1 < n and line[i + 1] == '"':
                    field.append('"')
                    i += 2
                    continue
                else:
                    # Closing quote
                    in_quotes = False
                    i += 1
                    continue
            else:
                field.append(ch)
                i += 1
        else:
            if ch == ',':
                # End of field
                fields.append(''.join(field))
                field = []
                i += 1
            elif ch == '"':
                # Opening quote
                in_quotes = True
                i += 1
            else:
                field.append(ch)
                i += 1

    # Append the last field
    fields.append(''.join(field))
    return fields


if __name__ == "__main__":
    # Simple self-test
    test_cases = [
        ('a,b,c', ['a', 'b', 'c']),
        ('"a","b","c"', ['a', 'b', 'c']),
        ('"a,b",c', ['a,b', 'c']),
        ('"a""b",c', ['a"b', 'c']),
        ('', ['']),
        (',,', ['', '', '']),
        ('"",', ['', '']),
        ('"a""",b', ['a"', 'b']),
    ]
    for inp, expected in test_cases:
        result = parse_delimited(inp)
        assert result == expected, f"Failed: {inp!r} -> {result!r} (expected {expected!r})"
    print("All tests passed.")
```