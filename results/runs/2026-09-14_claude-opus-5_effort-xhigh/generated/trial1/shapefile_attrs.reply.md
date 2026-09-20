```python
"""Read the attribute field names of an ESRI Shapefile.

A shapefile stores its attribute table in the ``.dbf`` sidecar, a dBASE table
whose header carries one 32-byte descriptor per field.  The field names can
therefore be recovered from that header alone, so this module parses it
directly instead of depending on a full vector I/O stack.

Importing this module has no side effects.
"""

from __future__ import annotations

import codecs
import os
import struct
from pathlib import Path

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_FIELD_DESC_SIZE = 32
_FIELD_NAME_SIZE = 11
_FIELD_TERMINATOR = 0x0D

# dBASE "language driver id" (header byte 29) -> codec, covering the values
# shapefile writers actually emit.  Unlisted ids fall back to sniffing.
_LDID_CODECS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
    0x57: "cp1252",  # GDAL writes this for "ANSI"
    0x58: "cp1252",
    0x59: "cp1252",
    0x64: "cp852",
    0x65: "cp866",
    0x6A: "cp737",
    0x6B: "cp857",
    0x78: "cp950",
    0x79: "cp949",
    0x7A: "cp936",
    0x7B: "cp932",
    0x7C: "cp874",
    0xC8: "cp1250",
    0xC9: "cp1251",
    0xCA: "cp1254",
    0xCB: "cp1253",
    0xCC: "cp1257",
}


def shapefile_attrs(path: str | os.PathLike[str]) -> list[str]:
    """Return the shapefile's attribute field names, in the order stored.

    ``path`` points at the ``.shp`` (the ``.dbf`` sidecar is located next to
    it; passing the ``.dbf`` directly also works).  Names are returned verbatim
    -- original case, duplicates and all -- with only the dBASE NUL/space
    padding removed.

    Raises FileNotFoundError if no ``.dbf`` sits alongside the shapefile, and
    ValueError if that file is too short to hold a dBASE header.
    """
    given = Path(path)
    dbf = given if given.suffix.lower() == ".dbf" else _sidecar(given, ".dbf")
    if dbf is None:
        raise FileNotFoundError(f"no .dbf attribute table alongside {given}")

    with dbf.open("rb") as handle:
        header = handle.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf} is too short to be a dBASE table")
        (header_length,) = struct.unpack_from("<H", header, 8)
        if header_length >= _HEADER_SIZE + _FIELD_DESC_SIZE + 1:
            region = handle.read(header_length - _HEADER_SIZE)
        else:
            # Implausible header length; lean on the field terminator instead.
            region = handle.read(_FIELD_DESC_SIZE * 256)

    encoding = _declared_encoding(dbf, header[29])

    names: list[str] = []
    for offset in range(0, len(region) - _FIELD_DESC_SIZE + 1, _FIELD_DESC_SIZE):
        if region[offset] in (_FIELD_TERMINATOR, 0x00):
            break  # end of the descriptor array
        raw = region[offset : offset + _FIELD_NAME_SIZE]
        raw = raw.split(b"\x00", 1)[0].rstrip(b" ")
        names.append(_decode(raw, encoding))
    return names


def _sidecar(path: Path, suffix: str) -> Path | None:
    """Locate a shapefile sidecar, tolerating sidecars with a different case."""
    for candidate in (path.with_suffix(suffix), path.with_suffix(suffix.upper())):
        if candidate.is_file():
            return candidate
    wanted = (path.stem + suffix).lower()
    try:
        entries = list(path.parent.iterdir())
    except OSError:
        return None
    for entry in entries:
        if entry.name.lower() == wanted and entry.is_file():
            return entry
    return None


def _declared_encoding(dbf: Path, ldid: int) -> str | None:
    """Encoding named by the ``.cpg`` sidecar, else by the language driver id."""
    cpg = _sidecar(dbf, ".cpg")
    if cpg is not None:
        try:
            label = cpg.read_bytes()[:64].decode("ascii", "ignore")
        except OSError:
            label = ""
        codec = _codec_from_label(label)
        if codec is not None:
            return codec
    return _LDID_CODECS.get(ldid)


def _codec_from_label(label: str) -> str | None:
    """Map a ``.cpg`` label ("UTF-8", "ANSI 1252", "LDID/87", ...) to a codec."""
    text = " ".join(label.split())
    if not text:
        return None
    if text.upper().startswith("LDID/"):
        try:
            return _LDID_CODECS.get(int(text[5:]))
        except ValueError:
            return None
    candidates = [text, text.replace(" ", "")]
    digits = text.rsplit(" ", 1)[-1]
    if digits.isdigit():
        candidates.append("utf-8" if digits == "65001" else "cp" + digits)
    for candidate in candidates:
        try:
            return codecs.lookup(candidate).name
        except LookupError:
            continue
    return None


def _decode(raw: bytes, encoding: str | None) -> str:
    """Decode a field name, degrading gracefully when the label is wrong."""
    for codec in (encoding, "utf-8"):
        if codec is None:
            continue
        try:
            return raw.decode(codec)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")  # never fails; preserves the raw bytes
```