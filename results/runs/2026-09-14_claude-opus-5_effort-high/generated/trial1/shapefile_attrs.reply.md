```python
"""Read the attribute field names of an ESRI Shapefile.

A shapefile's attribute table lives in the sibling ``.dbf`` file.  Its header is
a simple fixed-width structure, so it is parsed here directly with the standard
library: no GDAL/OGR binding is required just to list field names.
"""

from __future__ import annotations

import codecs
import os
from pathlib import Path

__all__ = ["shapefile_attrs"]

_HEADER_LEN = 32
_DESCRIPTOR_LEN = 32
_NAME_LEN = 11
_FIELD_TERMINATOR = 0x0D
_EOF_MARKER = 0x1A

# dBASE language driver id (header byte 29) -> Python codec.  Only the values
# writers of shapefiles realistically emit are listed; anything else falls back
# to latin-1, which round-trips every byte.
_LDID_ENCODINGS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
    0x08: "cp865",
    0x09: "cp437",
    0x0A: "cp850",
    0x0B: "cp437",
    0x0D: "cp437",
    0x0E: "cp850",
    0x0F: "cp437",
    0x10: "cp850",
    0x11: "cp437",
    0x12: "cp850",
    0x13: "cp932",
    0x14: "cp850",
    0x15: "cp437",
    0x16: "cp850",
    0x17: "cp865",
    0x18: "cp437",
    0x19: "cp437",
    0x1A: "cp850",
    0x1B: "cp437",
    0x1C: "cp863",
    0x1D: "cp850",
    0x1F: "cp852",
    0x22: "cp852",
    0x23: "cp852",
    0x24: "cp860",
    0x25: "cp850",
    0x26: "cp866",
    0x37: "cp850",
    0x40: "cp852",
    0x4D: "cp936",
    0x4E: "cp949",
    0x4F: "cp950",
    0x50: "cp874",
    0x57: "cp1252",
    0x58: "cp1252",
    0x59: "cp1252",
    0x64: "cp852",
    0x65: "cp866",
    0x66: "cp865",
    0x67: "cp861",
    0x6A: "cp737",
    0x6B: "cp857",
    0x78: "cp950",
    0x79: "cp949",
    0x7A: "cp936",
    0x7B: "cp932",
    0x7C: "cp874",
    0x86: "cp737",
    0x87: "cp852",
    0x88: "cp857",
    0xC8: "cp1250",
    0xC9: "cp1251",
    0xCA: "cp1254",
    0xCB: "cp1253",
    0xCC: "cp1257",
}


def shapefile_attrs(path):
    """Return the attribute field names of a shapefile, in file order.

    ``path`` points at the ``.shp`` file (the sibling ``.dbf`` is what gets
    read); a path to the ``.dbf`` itself is also accepted.  Names come back
    exactly as stored, with only the header's padding removed.

    Raises ``FileNotFoundError`` if no attribute table sits alongside ``path``
    and ``ValueError`` if that table's header is truncated.
    """
    dbf_path = _find_sidecar(path, "dbf")
    with open(dbf_path, "rb") as handle:
        header = handle.read(_HEADER_LEN)
        if len(header) < _HEADER_LEN:
            raise ValueError(f"truncated dBASE header in {dbf_path}")
        header_len = int.from_bytes(header[8:10], "little")
        language_driver = header[29]

        # The header length gives the field count directly, but some writers
        # leave it at zero, so it only ever serves as an upper bound and the
        # 0x0D terminator is what actually ends the loop.
        declared = max(header_len - _HEADER_LEN - 1, 0) // _DESCRIPTOR_LEN
        limit = declared if declared else None

        encoding = _resolve_encoding(dbf_path, language_driver)
        names = []
        while limit is None or len(names) < limit:
            descriptor = handle.read(_DESCRIPTOR_LEN)
            if len(descriptor) < _DESCRIPTOR_LEN:
                break
            if descriptor[0] in (_FIELD_TERMINATOR, _EOF_MARKER):
                break
            names.append(_decode_name(descriptor[:_NAME_LEN], encoding))
    return names


def _decode_name(raw, encoding):
    """Decode one NUL-padded field name out of a field descriptor."""
    raw = raw.split(b"\x00", 1)[0]
    try:
        name = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        name = raw.decode("latin-1")
    return name.rstrip()


def _resolve_encoding(dbf_path, language_driver):
    """Pick a codec from the ``.cpg`` sidecar, else from the language driver id."""
    declared = _read_cpg(dbf_path)
    if declared:
        return declared
    return _LDID_ENCODINGS.get(language_driver, "latin-1")


def _read_cpg(dbf_path):
    """Return the codec named by the ``.cpg`` sidecar, or ``None``."""
    try:
        cpg_path = _find_sidecar(dbf_path, "cpg")
    except FileNotFoundError:
        return None
    try:
        declared = cpg_path.read_text(encoding="ascii", errors="ignore").strip()
    except OSError:
        return None
    if not declared:
        return None
    if declared.isdigit():
        declared = "utf-8" if declared == "65001" else "cp" + declared
    try:
        codecs.lookup(declared)
    except LookupError:
        return None
    return declared


def _find_sidecar(path, extension):
    """Locate the sibling file with ``extension``, tolerating case differences."""
    source = Path(os.fspath(path))
    if source.suffix.lower() == "." + extension and source.is_file():
        return source
    for suffix in ("." + extension, "." + extension.upper()):
        candidate = source.with_suffix(suffix)
        if candidate.is_file():
            return candidate
    stem = source.stem.lower()
    try:
        entries = sorted(source.parent.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        if entry.stem.lower() == stem and entry.suffix.lower() == "." + extension:
            if entry.is_file():
                return entry
    raise FileNotFoundError(f"no .{extension} file alongside {source}")
```