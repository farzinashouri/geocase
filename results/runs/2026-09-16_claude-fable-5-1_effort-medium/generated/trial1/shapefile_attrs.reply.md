```python
"""Read attribute field names from an ESRI Shapefile.

A Shapefile's attributes live in the ``.dbf`` sidecar (dBASE III/IV format).
The field names are stored in the DBF header as fixed 32-byte field
descriptor records, each starting with an 11-byte NUL-padded name. This
module parses that header directly with the standard library.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

__all__ = ["shapefile_attrs"]

_HEADER_LEN = 32
_DESCRIPTOR_LEN = 32
_TERMINATOR = 0x0D

# dBASE language driver id (byte 29 of the header) -> codec, for the ids that
# commonly show up in Shapefiles. Anything unknown falls back to the .cpg
# sidecar, then to latin-1 (which never fails to decode).
_LDID_CODECS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
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
    0x7D: "cp1255",
    0x7E: "cp1256",
    0xC8: "cp1250",
    0xC9: "cp1251",
    0xCA: "cp1254",
    0xCB: "cp1253",
    0xCC: "cp1257",
}


def _find_sidecar(shp: Path, ext: str) -> Path | None:
    """Locate a sidecar file next to ``shp`` with the given extension.

    Tries the lowercase and uppercase extension first, then falls back to a
    case-insensitive directory scan (for mixed-case extensions on
    case-sensitive filesystems).
    """
    for candidate in (shp.with_suffix(ext.lower()), shp.with_suffix(ext.upper())):
        if candidate.is_file():
            return candidate
    parent = shp.parent if str(shp.parent) else Path(".")
    stem = shp.stem
    try:
        entries = os.listdir(parent)
    except OSError:
        return None
    for name in entries:
        p = Path(name)
        if p.stem == stem and p.suffix.lower() == ext.lower():
            full = parent / name
            if full.is_file():
                return full
    return None


def _codec_for(header: bytes, shp: Path) -> str:
    """Choose a text codec for field names from the .cpg sidecar or LDID."""
    cpg = _find_sidecar(shp, ".cpg")
    if cpg is not None:
        try:
            text = cpg.read_text(encoding="ascii", errors="ignore").strip()
        except OSError:
            text = ""
        if text:
            candidate = text.upper()
            if candidate.startswith("UTF-8") or candidate.startswith("UTF8"):
                candidate = "utf-8"
            elif candidate.isdigit():
                candidate = "cp" + candidate
            elif candidate.startswith("ISO"):
                candidate = candidate.replace("ISO", "iso", 1)
            try:
                "".encode(candidate)
                return candidate
            except LookupError:
                pass
    codec = _LDID_CODECS.get(header[29])
    return codec or "latin-1"


def _decode_name(raw: bytes, codec: str) -> str:
    """Decode an 11-byte field name, truncating at the first NUL."""
    nul = raw.find(b"\x00")
    if nul != -1:
        raw = raw[:nul]
    try:
        return raw.decode(codec)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("latin-1")


def shapefile_attrs(path: str | os.PathLike[str]) -> list[str]:
    """Return the attribute field names of a Shapefile, in file order.

    Parameters
    ----------
    path:
        Path to the ``.shp`` file (or to the ``.dbf`` directly). The ``.dbf``
        sidecar must sit alongside it with the same stem.

    Returns
    -------
    list[str]
        Field names exactly as stored in the DBF header (no case folding,
        no whitespace stripping beyond the NUL padding).

    Raises
    ------
    FileNotFoundError
        If no ``.dbf`` sidecar can be found.
    ValueError
        If the ``.dbf`` header is malformed.
    """
    shp = Path(path)
    if shp.suffix.lower() == ".dbf" and shp.is_file():
        dbf: Path | None = shp
    else:
        dbf = _find_sidecar(shp, ".dbf")
    if dbf is None:
        raise FileNotFoundError(f"No .dbf sidecar found for {shp}")

    with open(dbf, "rb") as fh:
        header = fh.read(_HEADER_LEN)
        if len(header) < _HEADER_LEN:
            raise ValueError(f"{dbf}: truncated DBF header")
        (header_len,) = struct.unpack("<H", header[8:10])
        if header_len < _HEADER_LEN + 1:
            raise ValueError(f"{dbf}: invalid DBF header length {header_len}")
        descriptors = fh.read(header_len - _HEADER_LEN)

    codec = _codec_for(header, shp)
    names: list[str] = []
    offset = 0
    while offset < len(descriptors):
        if descriptors[offset] == _TERMINATOR:
            break
        record = descriptors[offset : offset + _DESCRIPTOR_LEN]
        if len(record) < _DESCRIPTOR_LEN:
            raise ValueError(f"{dbf}: truncated field descriptor at byte {offset + _HEADER_LEN}")
        names.append(_decode_name(record[:11], codec))
        offset += _DESCRIPTOR_LEN
    return names
```