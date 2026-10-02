```python
import os
import struct
from typing import List


def shapefile_attrs(path: str) -> List[str]:
    """
    Return the attribute field names of an ESRI Shapefile.

    The function reads the associated .dbf file (same base name as the .shp file)
    and parses its header to extract field names in the order they appear.

    Parameters
    ----------
    path : str
        Path to the .shp file (or any path; the .dbf extension will be inferred).

    Returns
    -------
    list[str]
        List of field names exactly as stored in the file.

    Raises
    ------
    FileNotFoundError
        If the corresponding .dbf file does not exist.
    ValueError
        If the .dbf file is malformed or cannot be parsed.
    """
    base, _ = os.path.splitext(path)
    dbf_path = base + ".dbf"

    with open(dbf_path, "rb") as f:
        # Read the main header (32 bytes)
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("DBF file too small to contain a valid header")

        # Header structure (little-endian):
        #   byte 0: version
        #   bytes 1-3: last update (YY, MM, DD)
        #   bytes 4-7: number of records (uint32)
        #   bytes 8-9: header length in bytes (uint16)
        #   bytes 10-11: record length in bytes (uint16)
        #   bytes 12-31: reserved
        num_records = struct.unpack("<I", header[4:8])[0]
        header_len = struct.unpack("<H", header[8:10])[0]
        record_len = struct.unpack("<H", header[10:12])[0]

        # Field descriptors follow the main header. Each is 32 bytes.
        # The array of field descriptors is terminated by a single 0x0D byte.
        fields = []
        while True:
            desc = f.read(32)
            if len(desc) < 32:
                break
            if desc[0] == 0x0D:  # terminator
                break

            # Field name: first 11 bytes, null-padded
            name_bytes = desc[0:11]
            # Find first null byte; if none, take all 11 bytes
            null_pos = name_bytes.find(b"\x00")
            if null_pos >= 0:
                name_bytes = name_bytes[:null_pos]

            # Decode. DBF files typically use the system code page (often latin-1 / cp1252).
            # We try latin-1 first, which never fails, then fall back to ascii with replacement.
            try:
                field_name = name_bytes.decode("latin-1")
            except UnicodeDecodeError:
                field_name = name_bytes.decode("ascii", errors="replace")

            fields.append(field_name)

        # Optional sanity check: we should have consumed exactly header_len - 32 - 1 bytes
        # for field descriptors (the -1 accounts for the terminator byte).
        # But we don't enforce it strictly; we just return what we parsed.

    return fields
```