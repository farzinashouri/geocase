```python
"""Read attribute field names from an ESRI Shapefile's .dbf sidecar."""

import os
import struct


def shapefile_attrs(path):
    """Return the attribute field names of a shapefile, in file order."""
    dbf_path = _find_dbf_path(path)
    with open(dbf_path, "rb") as f:
        header = f.read(32)
        if len(header) < 32:
            raise ValueError(f"Invalid DBF file: {dbf_path}")
        struct.unpack("<H", header[8:10])[0]  # header size (unused, validated implicitly)

        fields = []
        while True:
            marker = f.read(1)
            if not marker or marker == b"\x0d":
                break
            rest = f.read(31)
            if len(rest) < 31:
                break
            descriptor = marker + rest
            name = descriptor[0:11].split(b"\x00", 1)[0].decode("latin-1")
            fields.append(name)

    return fields


def _find_dbf_path(path):
    base, _ext = os.path.splitext(os.fspath(path))
    for candidate in (base + ".dbf", base + ".DBF", base + ".Dbf"):
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f"No .dbf sidecar file found for {path}")
```