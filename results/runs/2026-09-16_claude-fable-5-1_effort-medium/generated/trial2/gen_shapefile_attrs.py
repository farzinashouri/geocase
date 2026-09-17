"""Read attribute field names from an ESRI Shapefile.

The attribute table of a Shapefile lives in the ``.dbf`` sidecar (dBASE III/IV
format). This module parses that file's header directly with the standard
library, so no third-party dependency is needed.
"""

from __future__ import annotations

import os
import struct

_HEADER_SIZE = 32
_FIELD_DESCRIPTOR_SIZE = 32
_FIELD_TERMINATOR = 0x0D
_FIELD_NAME_SIZE = 11


def _sidecar_path(shp_path: str, ext: str) -> str:
    """Return the sidecar with extension ``ext`` (e.g. ``.dbf``), matching case if needed."""
    base, _ = os.path.splitext(shp_path)
    for candidate in (base + ext.lower(), base + ext.upper()):
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f"Missing {ext} sidecar for Shapefile: {shp_path}")


def _dbf_encoding(shp_path: str) -> str:
    """Pick a decoding for field names: the ``.cpg`` file if present, else latin-1."""
    base, _ = os.path.splitext(shp_path)
    for candidate in (base + ".cpg", base + ".CPG"):
        try:
            with open(candidate, "rb") as fh:
                name = fh.read(64).decode("ascii", "ignore").strip()
        except OSError:
            continue
        if name:
            try:
                "".encode(name)  # validate the codec name
                return name
            except LookupError:
                break
    return "latin-1"


def shapefile_attrs(path: str) -> list[str]:
    """Return the attribute field names of the Shapefile at ``path`` in file order."""
    dbf_path = _sidecar_path(path, ".dbf")
    encoding = _dbf_encoding(path)

    with open(dbf_path, "rb") as fh:
        header = fh.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"Truncated dBASE header: {dbf_path}")
        (header_len,) = struct.unpack("<H", header[8:10])
        descriptors = fh.read(max(header_len - _HEADER_SIZE, 0))

    names: list[str] = []
    offset = 0
    while offset + _FIELD_DESCRIPTOR_SIZE <= len(descriptors):
        if descriptors[offset] == _FIELD_TERMINATOR:
            break
        raw = descriptors[offset : offset + _FIELD_NAME_SIZE]
        raw = raw.split(b"\x00", 1)[0]
        names.append(raw.decode(encoding, "replace"))
        offset += _FIELD_DESCRIPTOR_SIZE

    return names