```python
"""Read attribute field names from an ESRI Shapefile.

A shapefile's attribute table lives in the ``.dbf`` sidecar (dBASE format).
The field names are stored in the DBF header as a sequence of 32-byte field
descriptors, so we parse that header directly rather than pulling in a
dedicated shapefile library.
"""

import os
import struct


def _dbf_path(path):
    """Return the path to the ``.dbf`` sidecar for a shapefile path."""
    root, ext = os.path.splitext(path)
    # Preserve the case convention of the given extension where possible.
    if ext.isupper():
        return root + ".DBF"
    return root + ".dbf"


def shapefile_attrs(path):
    """Return the attribute field names of an ESRI Shapefile, in file order.

    Parameters
    ----------
    path : str | os.PathLike
        Path to the ``.shp`` file. Its sidecar ``.dbf`` (holding the
        attribute table) is expected alongside it.

    Returns
    -------
    list[str]
        The field names, exactly as stored in the file, in order.
    """
    path = os.fspath(path)
    dbf = _dbf_path(path)
    if not os.path.exists(dbf):
        # Fall back to whatever case the given path used, then the other.
        root = os.path.splitext(path)[0]
        for candidate in (root + ".dbf", root + ".DBF"):
            if os.path.exists(candidate):
                dbf = candidate
                break

    names = []
    with open(dbf, "rb") as f:
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("truncated or invalid DBF header: %r" % (dbf,))

        # Bytes 8-9 (little-endian) give the number of bytes in the full
        # header; field descriptors fill the space between the 32-byte main
        # header and the 0x0D terminator.
        header_len = struct.unpack("<H", header[8:10])[0]
        n_field_bytes = header_len - 32 - 1
        if n_field_bytes < 0:
            n_field_bytes = 0

        descriptors = f.read(n_field_bytes)

    for i in range(0, len(descriptors) - 31, 32):
        chunk = descriptors[i:i + 32]
        if chunk[:1] == b"\r":  # field terminator reached
            break
        # Field name: 11 bytes, null-padded/terminated ASCII.
        raw = chunk[:11].split(b"\x00", 1)[0]
        names.append(raw.decode("ascii", "replace"))

    return names
```