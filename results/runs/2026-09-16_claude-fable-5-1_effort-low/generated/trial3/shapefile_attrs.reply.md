```python
"""Read attribute field names from an ESRI Shapefile's DBF sidecar."""

from __future__ import annotations

import os
import struct

_HEADER_TERMINATOR = 0x0D
_FIELD_DESCRIPTOR_SIZE = 32
_HEADER_SIZE = 32


def _sidecar(path: str, ext: str) -> str:
    """Locate a sidecar with `ext`, tolerating upper/lower-case extensions."""
    base, _ = os.path.splitext(path)
    for candidate in (base + ext.lower(), base + ext.upper()):
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"No {ext} sidecar found for {path!r}")


def _encoding(path: str) -> str:
    """Pick a text encoding from the .cpg sidecar, else latin-1 (never fails)."""
    try:
        with open(_sidecar(path, ".cpg"), "r", encoding="ascii", errors="ignore") as fh:
            name = fh.read().strip()
    except (FileNotFoundError, OSError):
        return "latin-1"
    if not name:
        return "latin-1"
    # Typical values: "UTF-8", "ISO-8859-1", "1252", "LATIN1", "OEM 850".
    up = name.upper().replace(" ", "")
    if up.isdigit():
        name = "cp" + up
    elif up.startswith("OEM"):
        name = "cp" + up[3:]
    try:
        "".encode(name)
        return name
    except LookupError:
        return "latin-1"


def shapefile_attrs(path: str) -> list[str]:
    """Return attribute field names of the shapefile at `path`, in file order."""
    dbf_path = _sidecar(path, ".dbf")
    encoding = _encoding(path)
    names: list[str] = []
    with open(dbf_path, "rb") as fh:
        header = fh.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf_path!r} is not a valid DBF file (truncated header)")
        header_length = struct.unpack("<H", header[8:10])[0]
        # Field descriptors follow the 32-byte header and end at a 0x0D byte.
        limit = max(header_length, _HEADER_SIZE)
        offset = _HEADER_SIZE
        while offset + 1 <= limit:
            first = fh.read(1)
            if not first or first[0] == _HEADER_TERMINATOR:
                break
            rest = fh.read(_FIELD_DESCRIPTOR_SIZE - 1)
            if len(rest) < _FIELD_DESCRIPTOR_SIZE - 1:
                break
            raw_name = (first + rest)[:11]
            raw_name = raw_name.split(b"\x00", 1)[0]
            names.append(raw_name.decode(encoding, errors="replace"))
            offset += _FIELD_DESCRIPTOR_SIZE
    return names
```