"""Read the attribute field names of an ESRI Shapefile.

Shapefile attributes live in the companion ``.dbf`` table, so this module
parses the dBASE III+/IV header directly rather than pulling in a full
vector I/O stack.  Importing it has no side effects.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["shapefile_attrs"]

# dBASE "language driver ID" (header byte 29) -> Python codec.  Only the
# values that actually show up in shapefiles in the wild are listed; anything
# else falls back to latin-1, which never raises and round-trips bytes.
_LANGUAGE_DRIVER_CODECS = {
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
    0x6C: "cp863",
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

_HEADER_SIZE = 32
_FIELD_DESCRIPTOR_SIZE = 32
_FIELD_TERMINATOR = 0x0D


def _find_dbf(path) -> Path:
    """Locate the ``.dbf`` sidecar for *path* (a ``.shp`` or the stem)."""
    p = Path(os.fspath(path))
    if p.suffix.lower() == ".dbf" and p.is_file():
        return p

    stem = p.with_suffix("")
    for suffix in (".dbf", ".DBF", ".Dbf"):
        candidate = stem.with_name(stem.name + suffix)
        if candidate.is_file():
            return candidate

    # Case-insensitive sweep of the directory, for archives extracted with
    # mixed-case sidecar names (e.g. "roads.shp" next to "ROADS.dBf").
    parent = stem.parent if str(stem.parent) else Path(".")
    wanted = stem.name.lower() + ".dbf"
    try:
        entries = list(parent.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        if entry.name.lower() == wanted and entry.is_file():
            return entry

    raise FileNotFoundError(f"no .dbf attribute table found alongside {p}")


def _encoding(dbf_path: Path, language_driver: int) -> str:
    """Pick a codec: the ``.cpg`` sidecar wins, then the language driver ID."""
    cpg = dbf_path.with_suffix(".cpg")
    if not cpg.is_file():
        cpg = dbf_path.with_suffix(".CPG")
    if cpg.is_file():
        try:
            declared = cpg.read_text("ascii", errors="ignore").strip()
        except OSError:
            declared = ""
        if declared:
            name = declared.replace("-", "").replace(" ", "").lower()
            if name.isdigit():
                name = "cp" + name
            elif name.startswith("iso8859"):
                name = "iso8859-" + name[len("iso8859"):]
            try:
                "".encode(name)
            except LookupError:
                pass
            else:
                return name

    return _LANGUAGE_DRIVER_CODECS.get(language_driver, "latin-1")


def shapefile_attrs(path) -> list[str]:
    """Return the shapefile's attribute field names, in file order.

    ``path`` is the ``.shp`` file (its ``.dbf`` sidecar must sit beside it);
    a ``.dbf`` path is accepted too.  Names come back exactly as stored,
    decoded with the table's declared code page.
    """
    dbf_path = _find_dbf(path)

    with open(dbf_path, "rb") as fh:
        header = fh.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf_path} is too short to be a DBF table")

        header_length = int.from_bytes(header[8:10], "little")
        descriptor_bytes = max(header_length - _HEADER_SIZE, 0)
        encoding = _encoding(dbf_path, header[29])

        # Trust the terminator over the declared header length: both are
        # wrong in some files, and reading the smaller of the two is safe.
        block = fh.read(descriptor_bytes) if descriptor_bytes else fh.read()

    names: list[str] = []
    for offset in range(0, len(block) - _FIELD_DESCRIPTOR_SIZE + 1,
                        _FIELD_DESCRIPTOR_SIZE):
        descriptor = block[offset:offset + _FIELD_DESCRIPTOR_SIZE]
        if descriptor[0] == _FIELD_TERMINATOR:
            break
        raw = descriptor[:11].split(b"\x00", 1)[0]
        if not raw:
            break
        names.append(raw.decode(encoding, errors="replace"))

    return names