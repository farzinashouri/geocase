Tool access for a scratch test was denied, so the module below is verified by reading rather than by execution. It parses the `.dbf` sidecar header directly with the standard library, so importing has no side effects and no optional dependency is needed.

```python
"""Read attribute field names from an ESRI Shapefile's .dbf sidecar."""

from __future__ import annotations

import os
import struct

__all__ = ["shapefile_attrs"]

_DBF_HEADER_SIZE = 32
_FIELD_TERMINATOR = 0x0D

# dBase language-driver ID (header byte 29) -> Python codec name.
_LDID_CODECS = {
    0x01: "cp437", 0x02: "cp850", 0x03: "cp1252", 0x08: "cp865",
    0x09: "cp437", 0x0A: "cp850", 0x0B: "cp437", 0x0D: "cp437",
    0x0E: "cp850", 0x0F: "cp437", 0x10: "cp850", 0x11: "cp437",
    0x12: "cp850", 0x13: "cp932", 0x14: "cp850", 0x15: "cp437",
    0x16: "cp850", 0x17: "cp865", 0x18: "cp437", 0x19: "cp437",
    0x1A: "cp850", 0x1B: "cp437", 0x1C: "cp863", 0x1D: "cp850",
    0x1F: "cp852", 0x22: "cp852", 0x23: "cp852", 0x24: "cp860",
    0x25: "cp850", 0x26: "cp866", 0x37: "cp850", 0x40: "cp852",
    0x4D: "cp936", 0x4E: "cp949", 0x4F: "cp950", 0x50: "cp874",
    0x57: "cp1252", 0x58: "cp1252", 0x59: "cp1252", 0x64: "cp852",
    0x65: "cp866", 0x66: "cp865", 0x67: "cp861", 0x6A: "cp737",
    0x6B: "cp857", 0x6C: "cp863", 0x78: "cp950", 0x79: "cp949",
    0x7A: "cp936", 0x7B: "cp932", 0x7C: "cp874", 0x7D: "cp1255",
    0x7E: "cp1256", 0x86: "cp737", 0x87: "cp852", 0x88: "cp857",
    0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253",
    0xCC: "cp1257",
}


def _sidecar(path: str | os.PathLike, ext: str) -> str:
    """Return the path of the ``ext`` sidecar next to ``path``.

    The extension is tried in the same letter case as the input first, then
    the other case; if neither exists the lower-case name is returned.
    """
    stem, src_ext = os.path.splitext(os.fspath(path))
    if src_ext.isupper():
        candidates = (ext.upper(), ext.lower())
    else:
        candidates = (ext.lower(), ext.upper())
    for candidate in candidates:
        full = stem + candidate
        if os.path.isfile(full):
            return full
    return stem + ext.lower()


def _codec_exists(name: str) -> bool:
    try:
        b"".decode(name)
    except (LookupError, TypeError):
        return False
    return True


def _codepage(path: str | os.PathLike, ldid: int) -> str:
    """Choose a codec for field names: ``.cpg`` sidecar, else LDID byte, else cp1252."""
    cpg = _sidecar(path, ".cpg")
    if os.path.isfile(cpg):
        try:
            with open(cpg, "r", encoding="ascii", errors="ignore") as fh:
                name = fh.read().strip()
        except OSError:
            name = ""
        if name:
            compact = name.lower().replace("-", "").replace("_", "").replace(" ", "")
            for candidate in (name, compact, "cp" + compact, compact.replace("windows", "cp")):
                if _codec_exists(candidate):
                    return candidate
    return _LDID_CODECS.get(ldid, "cp1252")


def _decode(raw: bytes, encoding: str) -> str:
    for enc in (encoding, "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1")


def shapefile_attrs(path: str | os.PathLike) -> list[str]:
    """Return the attribute field names of a Shapefile, in file order.

    ``path`` is the ``.shp`` file; the names are read from the ``.dbf`` sidecar
    that accompanies it and are returned exactly as stored in the DBF field
    descriptors (only the null padding is removed).
    """
    dbf_path = _sidecar(path, ".dbf")
    with open(dbf_path, "rb") as fh:
        header = fh.read(_DBF_HEADER_SIZE)
        if len(header) < _DBF_HEADER_SIZE:
            raise ValueError(f"{dbf_path}: truncated DBF header")
        version = header[0]
        header_len = struct.unpack_from("<H", header, 8)[0]
        ldid = header[29]
        # dBase 7 uses 48-byte field descriptors with 32-byte names; every
        # other variant found in shapefiles uses 32-byte descriptors, 11-byte names.
        if version & 0x07 == 0x04:
            desc_size, name_size = 48, 32
        else:
            desc_size, name_size = 32, 11
        descriptors = fh.read(max(header_len - _DBF_HEADER_SIZE, 0))

    encoding = _codepage(path, ldid)
    names: list[str] = []
    offset = 0
    while offset < len(descriptors) and descriptors[offset] != _FIELD_TERMINATOR:
        chunk = descriptors[offset : offset + desc_size]
        if len(chunk) < desc_size:
            break
        raw_name = chunk[:name_size].split(b"\x00", 1)[0]
        names.append(_decode(raw_name, encoding))
        offset += desc_size
    return names
```