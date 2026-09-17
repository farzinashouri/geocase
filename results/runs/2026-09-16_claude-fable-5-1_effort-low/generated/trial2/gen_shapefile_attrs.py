"""Read attribute field names from an ESRI Shapefile.

The attribute table of a Shapefile lives in the ``.dbf`` sidecar (dBASE III+
format).  Field descriptors are 32-byte records starting at byte 32 of the
header, terminated by a 0x0D byte.  Each descriptor stores the field name in
its first 11 bytes, NUL-padded.
"""

from __future__ import annotations

import os
import struct
from typing import List


def _dbf_path(path: str) -> str:
    """Return the ``.dbf`` sidecar path for a ``.shp`` path (case-tolerant)."""
    root, ext = os.path.splitext(path)
    if ext.lower() == ".dbf":
        return path
    for candidate in (root + ".dbf", root + ".DBF"):
        if os.path.exists(candidate):
            return candidate
    return root + ".dbf"


def shapefile_attrs(path: str) -> List[str]:
    """Return the attribute field names of a Shapefile in file order."""
    dbf = _dbf_path(path)
    with open(dbf, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError(f"{dbf}: truncated DBF header")
        header_len = struct.unpack("<H", header[8:10])[0]
        descriptor_bytes = fh.read(max(header_len - 32, 0))

    names: List[str] = []
    offset = 0
    while offset + 32 <= len(descriptor_bytes):
        record = descriptor_bytes[offset : offset + 32]
        if record[0] == 0x0D:
            break
        raw = record[:11].split(b"\x00", 1)[0]
        names.append(raw.decode("latin-1"))
        offset += 32
    return names