import csv

def parse_delimited(line):
    """
    Parse a single RFC 4180 CSV record.

    Args:
        line: A string containing one CSV record (no trailing newline).

    Returns:
        A list of field strings. Empty fields are preserved.
    """
    # csv.reader returns an iterator over rows; we feed it a single-element list.
    return next(csv.reader([line]))