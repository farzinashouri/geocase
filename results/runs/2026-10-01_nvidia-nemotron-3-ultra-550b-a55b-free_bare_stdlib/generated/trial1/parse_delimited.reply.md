```python
def parse_delimited(line):
    """Parse a single CSV line according to RFC 4180.

    Args:
        line: A string containing one CSV record (no trailing newline).

    Returns:
        A list of field strings.
    """
    fields = []
    field = []
    in_quotes = False
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if in_quotes:
            if c == '"':
                # Check for escaped quote
                if i + 1 < n and line[i + 1] == '"':
                    field.append('"')
                    i += 2
                else:
                    # Closing quote
                    in_quotes = False
                    i += 1
            else:
                field.append(c)
                i += 1
        else:
            if c == ',':
                # End of field
                fields.append(''.join(field))
                field = []
                i += 1
            elif c == '"':
                # Start of quoted field
                in_quotes = True
                i += 1
            else:
                field.append(c)
                i += 1
    # Append the last field
    fields.append(''.join(field))
    return fields
```