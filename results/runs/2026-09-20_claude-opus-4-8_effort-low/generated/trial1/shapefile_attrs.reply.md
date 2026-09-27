```python
"""Read attribute field names from an ESRI Shapefile's DBF sidecar."""

import os
import struct


def shapefile_attrs(path):
    """Return the attribute field names of a shapefile, in file order.

    Parameters
    ----------
    path : str or os.PathLike
        Path to the ``.shp`` file (its ``.dbf`` sidecar must be alongside it).

    Returns
    -------
    list[str]
        Field names exactly as stored in the DBF file, in order.
    """
    # Attribute fields live in the .dbf sidecar, not the .shp geometry file.
    dbf_path = _dbf_path(path)

    with open(dbf_path, "rb") as fh:
        # dBASE header: byte 8-9 holds the header length (little-endian uint16).
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError("Truncated DBF header: %r" % (dbf_path,))
        header_length = struct.unpack("<H", header[8:10])[0]

        # Each field descriptor is 32 bytes; they run from offset 32 until the
        # 0x0D terminator that precedes the record data.
        names = []
        while True:
            descriptor = fh.read(32)
            if len(descriptor) < 32:
                break
            if descriptor[0:1] == b"\r":  # 0x0D terminator
                break
            if fh.tell() > header_length:
                break
            # Name is the first 11 bytes, NUL-padded/terminated.
            raw_name = descriptor[0:11].split(b"\x00", 1)[0]
            names.append(raw_name.decode("ascii"))

    return names


def _dbf_path(path):
    """Derive the .dbf sidecar path from a shapefile path."""
    p = os.fspath(path)
    root, ext = os.path.splitext(p)
    if ext.lower() == ".shp":
        base = root
    elif ext.lower() == ".dbf":
        return p
    else:
        base = p
    # Match the case of the .shp extension for the sidecar where possible.
    if ext.isupper():
        return base + ".DBF"
    return base + ".dbf"
```