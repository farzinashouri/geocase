Writing a stdlib-only module that parses the `.dbf` sidecar header directly.

```python
"""Read attribute field names from an ESRI Shapefile.

A Shapefile stores its attribute table in a dBase (``.dbf``) sidecar file.
The field names live in the ``.dbf`` header as a sequence of fixed-size
field descriptors, terminated by ``0x0D``. This module parses that header
directly with the standard library, so no optional dependencies are needed.
"""

from __future__ import annotations

import os
import struct

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_FIELD_TERMINATOR = 0x0D
_DBASE7_VERSION_MASK = 0x07
_DBASE7_VERSION = 0x04


def _sidecar(path: str, ext: str) -> str:
    """Return the sidecar path for *path* with extension *ext*.

    Prefers the same case as the ``.shp`` extension and falls back to
    lower/upper case variants that actually exist on disk.
    """
    base, shp_ext = os.path.splitext(path)
    if shp_ext.isupper():
        candidates = [base + ext.upper(), base + ext.lower()]
    else:
        candidates = [base + ext.lower(), base + ext.upper()]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


def _encoding(path: str) -> str:
    """Determine the text encoding of the ``.dbf`` from a ``.cpg`` file, if present."""
    cpg = _sidecar(path, ".cpg")
    try:
        with open(cpg, "rb") as fh:
            raw = fh.read(64).split(b"\n", 1)[0].strip()
    except OSError:
        return "latin-1"
    name = raw.decode("ascii", "ignore").strip()
    if not name:
        return "latin-1"
    lowered = name.lower().replace("-", "").replace("_", "")
    if lowered in {"utf8", "65001"}:
        return "utf-8"
    if lowered.isdigit():
        return "cp" + lowered
    if lowered.startswith("iso8859"):
        return "iso-8859-" + lowered[len("iso8859"):]
    try:
        "".encode(name)
    except LookupError:
        return "latin-1"
    return name


def _decode_name(raw: bytes, encoding: str) -> str:
    """Decode a raw, null-padded field-name buffer."""
    raw = raw.split(b"\x00", 1)[0].rstrip(b" ")
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("latin-1")


def shapefile_attrs(path: str) -> list[str]:
    """Return the attribute field names of the Shapefile at *path*.

    Parameters
    ----------
    path:
        Path to the ``.shp`` file. The ``.dbf`` sidecar is located next to it.

    Returns
    -------
    list[str]
        Field names in the order they appear in the ``.dbf`` header,
        exactly as stored (no case folding or renaming).

    Raises
    ------
    FileNotFoundError
        If the ``.dbf`` sidecar does not exist.
    ValueError
        If the ``.dbf`` header is malformed.
    """
    dbf_path = _sidecar(path, ".dbf")
    with open(dbf_path, "rb") as fh:
        header = fh.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf_path}: truncated dBase header")
        version = header[0]
        (header_len,) = struct.unpack("<H", header[8:10])
        if header_len < _HEADER_SIZE:
            raise ValueError(f"{dbf_path}: invalid header length {header_len}")
        descriptors = fh.read(header_len - _HEADER_SIZE)

    if (version & _DBASE7_VERSION_MASK) == _DBASE7_VERSION:
        descriptor_size, name_size = 48, 32
    else:
        descriptor_size, name_size = 32, 11

    encoding = _encoding(path)
    names: list[str] = []
    offset = 0
    while offset < len(descriptors):
        if descriptors[offset] == _FIELD_TERMINATOR:
            break
        chunk = descriptors[offset : offset + descriptor_size]
        if len(chunk) < descriptor_size:
            raise ValueError(f"{dbf_path}: truncated field descriptor")
        names.append(_decode_name(chunk[:name_size], encoding))
        offset += descriptor_size
    return names
```