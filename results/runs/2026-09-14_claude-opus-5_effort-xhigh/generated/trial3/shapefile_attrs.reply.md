```python
"""Read the attribute field names of an ESRI Shapefile.

A shapefile stores its attribute table in a dBASE (``.dbf``) sidecar that sits
next to the ``.shp`` geometry file.  The field names live in the ``.dbf``
header, so they can be read directly with the standard library -- no GDAL/OGR
binding required.

Importing this module has no side effects.
"""

from __future__ import annotations

import codecs
import os
import struct
from typing import Optional

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_FIELD_DESC_SIZE = 32
_FIELD_NAME_SIZE = 11
_HEADER_TERMINATOR = 0x0D

# dBASE language driver id (byte 29 of the header) -> Python codec.  Only the
# values seen in the wild are listed; anything else falls back to latin-1.
_LDID_ENCODINGS = {
    0x01: "cp437", 0x02: "cp850", 0x03: "cp1252", 0x04: "mac_roman",
    0x64: "cp852", 0x65: "cp866", 0x66: "cp865", 0x67: "cp861",
    0x6A: "cp737", 0x6B: "cp857", 0x78: "cp950", 0x79: "cp949",
    0x7A: "cp936", 0x7B: "cp932", 0x7C: "cp874", 0x7D: "cp1255",
    0x7E: "cp1256", 0x87: "cp852", 0x88: "cp1252", 0x89: "cp1253",
    0x8A: "cp1254", 0x8C: "cp1255", 0x8D: "cp1256", 0xC8: "cp1250",
    0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253",
}


def shapefile_attrs(path) -> list[str]:
    """Return the shapefile's attribute field names, in file order.

    Parameters
    ----------
    path:
        Path to the ``.shp`` file (or to any sibling sharing its base name).
        The ``.dbf`` sidecar is expected alongside it.

    Returns
    -------
    list[str]
        Field names exactly as stored, preserving case and order.  A shapefile
        whose attribute table has no fields yields an empty list.

    Raises
    ------
    FileNotFoundError
        If no ``.dbf`` sidecar can be found for ``path``.
    ValueError
        If the ``.dbf`` header is truncated or malformed.
    """
    dbf_path = _find_sidecar(path, ".dbf")
    if dbf_path is None:
        raise FileNotFoundError(
            f"no .dbf sidecar found alongside {os.fspath(path)!r}"
        )

    with open(dbf_path, "rb") as handle:
        header = handle.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf_path!r} is too short to be a DBF file")
        language_driver = header[29]
        header_length = struct.unpack_from("<H", header, 8)[0]
        if header_length < _HEADER_SIZE + 1:
            raise ValueError(
                f"{dbf_path!r} declares an impossible header length "
                f"({header_length} bytes)"
            )
        descriptors = handle.read(header_length - _HEADER_SIZE)

    encoding = _resolve_encoding(path, language_driver)

    names: list[str] = []
    last_start = len(descriptors) - _FIELD_DESC_SIZE
    for offset in range(0, last_start + 1, _FIELD_DESC_SIZE):
        chunk = descriptors[offset:offset + _FIELD_DESC_SIZE]
        # 0x0D terminates the descriptor array; a NUL means an unused slot.
        if chunk[0] in (_HEADER_TERMINATOR, 0x00):
            break
        raw_name = chunk[:_FIELD_NAME_SIZE].split(b"\x00", 1)[0]
        names.append(_decode(raw_name, encoding).strip())
    return names


def _find_sidecar(path, suffix: str) -> Optional[str]:
    """Locate a sibling file with the given suffix, ignoring extension case."""
    base = os.path.splitext(os.fspath(path))[0]
    for candidate in (base + suffix.lower(), base + suffix.upper()):
        if os.path.isfile(candidate):
            return candidate

    # Case-sensitive filesystems may hold e.g. "roads.Dbf".
    directory, stem = os.path.split(base)
    wanted = (stem + suffix).lower()
    try:
        entries = os.listdir(directory or os.curdir)
    except OSError:
        return None
    for entry in entries:
        if entry.lower() == wanted:
            found = os.path.join(directory, entry)
            if os.path.isfile(found):
                return found
    return None


def _resolve_encoding(path, language_driver: int) -> Optional[str]:
    """Pick the codec for field names: the .cpg sidecar wins, then the LDID."""
    cpg_path = _find_sidecar(path, ".cpg")
    if cpg_path is not None:
        try:
            with open(cpg_path, "rb") as handle:
                declared = handle.read(256).decode("ascii", "ignore")
        except OSError:
            declared = ""
        encoding = _encoding_from_cpg(declared)
        if encoding is not None:
            return encoding
    return _LDID_ENCODINGS.get(language_driver)


def _encoding_from_cpg(declared: str) -> Optional[str]:
    """Translate .cpg contents ("UTF-8", "65001", "LDID/87", ...) to a codec."""
    declared = declared.strip()
    if not declared:
        return None
    if declared.upper().startswith("LDID/"):
        try:
            return _LDID_ENCODINGS.get(int(declared[5:]))
        except ValueError:
            return None

    candidates = [declared.replace(" ", "")]
    if declared.isdigit():
        candidates.insert(0, "cp" + declared)
    for candidate in candidates:
        try:
            codecs.lookup(candidate)
        except LookupError:
            continue
        return candidate
    return None


def _decode(raw: bytes, encoding: Optional[str]) -> str:
    """Decode a field name, falling back to latin-1 (which never fails)."""
    if encoding:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass
    return raw.decode("latin-1")
```