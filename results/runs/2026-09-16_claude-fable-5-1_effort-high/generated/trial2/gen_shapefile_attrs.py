"""Read attribute field names from an ESRI Shapefile.

The attribute table of a Shapefile lives in the ``.dbf`` sidecar (dBase III/IV
format). This module parses that file's header directly with the standard
library, so no third-party vector driver is needed.

DBF layout (all little-endian):
    bytes  0..31   file header; byte 8-9 = uint16 total header length,
                   byte 29 = language driver id (LDID)
    bytes 32..     32-byte field descriptors, one per attribute column,
                   terminated by a single 0x0D byte
    each descriptor: bytes 0..10 = field name, NUL-padded to 11 bytes
"""

from __future__ import annotations

import codecs
import os
import struct
from pathlib import Path
from typing import Optional

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_DESCRIPTOR_SIZE = 32
_TERMINATOR = 0x0D

# Language driver id -> Python codec, for the LDIDs commonly emitted by
# shapefile writers. Anything unknown falls back to latin-1 (never fails).
_LDID_CODECS = {
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
    0x6C: "cp863",
    0x78: "cp950",
    0x79: "cp949",
    0x7A: "cp936",
    0x7B: "cp932",
    0x7C: "cp874",
    0x7D: "cp1255",
    0x7E: "cp1256",
    0x86: "cp737",
    0x87: "cp852",
    0x88: "cp857",
    0xC8: "cp1250",
    0xC9: "cp1251",
    0xCA: "cp1254",
    0xCB: "cp1253",
    0xCC: "cp1257",
}


def _sidecar(path: Path, ext: str) -> Optional[Path]:
    """Return the sidecar file with extension ``ext`` (e.g. ``".dbf"``).

    Tries the given case, then lower- and upper-case variants, so that
    ``roads.shp`` finds ``roads.dbf`` or ``roads.DBF``. Returns ``None`` if
    nothing exists.
    """
    stem = path.with_suffix("")
    for candidate in (ext, ext.lower(), ext.upper()):
        p = Path(str(stem) + candidate)
        if p.is_file():
            return p
    return None


def _codec_from_cpg(cpg_path: Path) -> Optional[str]:
    """Derive a Python codec name from a ``.cpg`` sidecar, if it is usable."""
    try:
        raw = cpg_path.read_text(encoding="ascii", errors="ignore").strip()
    except OSError:
        return None
    if not raw:
        return None
    name = raw.upper()
    if name.startswith("LDID/"):
        try:
            return _LDID_CODECS.get(int(name[5:], 10))
        except ValueError:
            return None
    # Normalise common spellings: "ISO 8859-1", "ISO-8859-1", "UTF-8", "1252".
    if name.isdigit():
        name = "cp" + name
    name = name.replace(" ", "-")
    try:
        return codecs.lookup(name).name
    except LookupError:
        return None


def _decode(raw: bytes, codec: str) -> str:
    try:
        return raw.decode(codec)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("latin-1")


def shapefile_attrs(path: "str | os.PathLike[str]") -> list[str]:
    """Return the attribute field names of a Shapefile, in file order.

    ``path`` may point at the ``.shp`` (or any other sidecar); the ``.dbf``
    is located alongside it. Field names are returned exactly as stored,
    with only the NUL padding of the 11-byte name slot removed.

    Raises ``FileNotFoundError`` if no ``.dbf`` sidecar exists and
    ``ValueError`` if the ``.dbf`` header is malformed.
    """
    src = Path(os.fspath(path))
    dbf = src if src.suffix.lower() == ".dbf" and src.is_file() else _sidecar(src, ".dbf")
    if dbf is None:
        raise FileNotFoundError(f"no .dbf attribute table found alongside {src}")

    with open(dbf, "rb") as fh:
        header = fh.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf}: truncated DBF header")
        (header_len,) = struct.unpack_from("<H", header, 8)
        if header_len < _HEADER_SIZE + 1:
            raise ValueError(f"{dbf}: invalid DBF header length {header_len}")
        descriptors = fh.read(header_len - _HEADER_SIZE)

    # Pick a text codec: .cpg sidecar first, then the LDID byte, then latin-1.
    codec: Optional[str] = None
    cpg = _sidecar(src, ".cpg")
    if cpg is not None:
        codec = _codec_from_cpg(cpg)
    if codec is None:
        codec = _LDID_CODECS.get(header[29], "latin-1")

    names: list[str] = []
    offset = 0
    while offset < len(descriptors):
        if descriptors[offset] == _TERMINATOR:
            break
        block = descriptors[offset : offset + _DESCRIPTOR_SIZE]
        if len(block) < _DESCRIPTOR_SIZE:
            raise ValueError(f"{dbf}: truncated field descriptor at byte {_HEADER_SIZE + offset}")
        raw_name = block[:11].split(b"\x00", 1)[0]
        names.append(_decode(raw_name, codec))
        offset += _DESCRIPTOR_SIZE
    return names