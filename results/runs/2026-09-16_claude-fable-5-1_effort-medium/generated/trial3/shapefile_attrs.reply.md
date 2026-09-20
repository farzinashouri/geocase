```python
"""Read attribute field names from an ESRI Shapefile's DBF sidecar."""

from __future__ import annotations

import os
import struct


def _find_dbf(shp_path: str) -> str:
    base, _ = os.path.splitext(shp_path)
    for ext in (".dbf", ".DBF"):
        candidate = base + ext
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f"No .dbf sidecar found for {shp_path!r}")


def _codepage(shp_path: str, ldid: int) -> str:
    base, _ = os.path.splitext(shp_path)
    for ext in (".cpg", ".CPG"):
        candidate = base + ext
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="ascii", errors="ignore") as fh:
                    name = fh.read().strip()
                if name:
                    "".encode(name)  # validate codec name
                    return name
            except (LookupError, OSError):
                pass
    ldid_map = {0x01: "cp437", 0x02: "cp850", 0x03: "cp1252", 0x57: "cp1252",
                0x64: "cp852", 0x65: "cp866", 0x66: "cp865", 0x67: "cp861",
                0x6A: "cp737", 0x6B: "cp857", 0x78: "cp950", 0x79: "cp949",
                0x7A: "cp936", 0x7B: "cp932", 0x7C: "cp874", 0x7D: "cp1255",
                0x7E: "cp1256", 0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254",
                0xCB: "cp1253"}
    return ldid_map.get(ldid, "latin-1")


def shapefile_attrs(path: str) -> list[str]:
    """Return the attribute field names of a Shapefile, in file order."""
    dbf_path = _find_dbf(path)
    with open(dbf_path, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError(f"{dbf_path!r}: truncated DBF header")
        header_len = struct.unpack("<H", header[8:10])[0]
        ldid = header[29]
        encoding = _codepage(path, ldid)
        names: list[str] = []
        offset = 32
        while offset + 32 <= header_len:
            desc = fh.read(32)
            if len(desc) < 32 or desc[0] == 0x0D:
                break
            raw = desc[:11].split(b"\x00", 1)[0]
            names.append(raw.decode(encoding, errors="replace"))
            offset += 32
    return names
```