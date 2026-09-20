"""Read attribute field names from an ESRI Shapefile.

The attribute table of a shapefile lives in its ``.dbf`` sidecar, a dBASE
table.  Only the table *header* is needed to recover the field names, so this
module parses that header directly and never reads the records.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["shapefile_attrs"]

# dBASE "language driver id" (byte 29 of the header) -> Python codec name.
# Only the values that occur in practice in shapefiles are listed; anything
# else falls back to latin-1, which never raises and round-trips byte values.
_LDID_ENCODINGS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
    0x04: "mac_roman",
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

_FIELD_TERMINATOR = 0x0D
_DBASE7_VERSIONS = frozenset({0x04, 0x84, 0x8B, 0x8E})


def _sibling(path: Path, suffix: str) -> Path | None:
    """Return the sidecar of ``path`` with ``suffix``, matching case-insensitively."""
    for candidate in (path.with_suffix(suffix), path.with_suffix(suffix.upper())):
        if candidate.is_file():
            return candidate
    # Fall back to a case-insensitive scan for mixed-case names such as ".Dbf".
    stem = path.stem.lower()
    want = suffix.lower()
    try:
        entries = list(path.parent.iterdir())
    except OSError:
        return None
    for entry in entries:
        if entry.stem.lower() == stem and entry.suffix.lower() == want and entry.is_file():
            return entry
    return None


def _encoding(dbf_path: Path, ldid: int) -> str:
    """Pick the codec for field names: the .cpg sidecar wins over the LDID byte."""
    cpg = _sibling(dbf_path, ".cpg")
    if cpg is not None:
        try:
            declared = cpg.read_text(encoding="ascii", errors="ignore").strip()
        except OSError:
            declared = ""
        if declared:
            name = declared.replace("-", "").replace(" ", "").lower()
            if name.isdigit():  # bare code page number, e.g. "1252"
                declared = "cp" + name
            elif name.startswith("cp") and name[2:].isdigit():
                declared = name
            try:
                "".encode(declared)
            except LookupError:
                pass
            else:
                return declared
    return _LDID_ENCODINGS.get(ldid, "latin-1")


def _decode(raw: bytes, encoding: str) -> str:
    name = raw.split(b"\x00", 1)[0]
    return name.decode(encoding, errors="replace").rstrip()


def shapefile_attrs(path: str | os.PathLike[str]) -> list[str]:
    """Return the attribute field names of a shapefile, in file order.

    ``path`` points at the ``.shp`` (the ``.dbf`` sidecar must sit beside it);
    a ``.dbf`` path is accepted directly too.  Names are returned exactly as
    stored, decoded with the encoding declared by the ``.cpg`` sidecar or the
    table's language-driver id.
    """
    path = Path(path)
    if path.suffix.lower() == ".dbf":
        dbf_path: Path | None = path if path.is_file() else None
    else:
        dbf_path = _sibling(path, ".dbf")
    if dbf_path is None:
        raise FileNotFoundError(f"no .dbf attribute table found alongside {path}")

    with open(dbf_path, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError(f"{dbf_path}: truncated dBASE header")
        version = header[0]
        header_length = int.from_bytes(header[8:10], "little")
        encoding = _encoding(dbf_path, header[29])

        if version in _DBASE7_VERSIONS:
            descriptor_size, name_size, start = 48, 32, 68
        else:
            descriptor_size, name_size, start = 32, 11, 32

        # header_length covers the whole header including the terminator byte;
        # ignore it when it is obviously bogus and just read to the terminator.
        limit = header_length - start if header_length > start else -1
        fh.seek(start)
        block = fh.read(limit) if limit > 0 else fh.read()

    names: list[str] = []
    for offset in range(0, len(block), descriptor_size):
        descriptor = block[offset : offset + descriptor_size]
        if not descriptor or descriptor[0] == _FIELD_TERMINATOR:
            break
        if len(descriptor) < descriptor_size:
            break
        name = _decode(descriptor[:name_size], encoding)
        if name:
            names.append(name)
    return names