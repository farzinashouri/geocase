"""Read attribute field names from an ESRI Shapefile.

The field names live in the companion dBASE (.dbf) table, so this parses the
.dbf header directly -- no third-party readers needed.
"""

from __future__ import annotations

import os

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_FIELD_DESC_SIZE = 32
_FIELD_TERMINATOR = 0x0D

# dBASE "language driver ID" (byte 29 of the header) -> codec, for the values
# ESRI actually writes. Anything unlisted falls back to latin-1, which never
# raises and round-trips bytes for single-byte pages.
_LDID_CODECS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
    0x08: "cp865",
    0x09: "cp437",
    0x0A: "cp850",
    0x4D: "cp936",
    0x4E: "cp949",
    0x4F: "cp932",
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


def _sidecar(path, ext):
    """Path to a sidecar file, matching the case of an existing file if any."""
    stem = os.path.splitext(path)[0]
    for candidate in (stem + ext.lower(), stem + ext.upper()):
        if os.path.exists(candidate):
            return candidate
    return stem + ext.lower()


def _codepage(path, ldid):
    """Resolve the .dbf text encoding from the .cpg sidecar, else the LDID."""
    cpg = _sidecar(path, ".cpg")
    try:
        with open(cpg, "rb") as fh:
            declared = fh.read(256).decode("ascii", "ignore").strip()
    except OSError:
        declared = ""

    if declared:
        name = declared.lower().replace("-", "").replace(" ", "")
        if name.isdigit():
            name = "cp" + name
        elif name.startswith("iso8859"):
            name = "iso8859-" + name[len("iso8859"):]
        try:
            "".encode(name)
            return name
        except LookupError:
            pass

    return _LDID_CODECS.get(ldid, "latin-1")


def shapefile_attrs(path):
    """Return the shapefile's attribute field names, in file order.

    Args:
        path: Path to the ``.shp`` (or its ``.dbf``); sidecars are expected
            alongside it.

    Returns:
        list[str]: Field names exactly as stored, excluding the deletion flag.
    """
    dbf = path if os.path.splitext(path)[1].lower() == ".dbf" else _sidecar(path, ".dbf")

    with open(dbf, "rb") as fh:
        header = fh.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError("%s: truncated dBASE header" % dbf)

        encoding = _codepage(path, header[29])

        # Bytes 8-9 give the offset of the first data record; the field
        # descriptors fill the space between the header and that offset.
        first_record = int.from_bytes(header[8:10], "little")
        descriptors_len = max(first_record - _HEADER_SIZE, 0)
        block = fh.read(descriptors_len) if descriptors_len else fh.read()

    names = []
    for start in range(0, len(block) - _FIELD_DESC_SIZE + 1, _FIELD_DESC_SIZE):
        if block[start] == _FIELD_TERMINATOR:
            break
        raw = block[start:start + 11].split(b"\x00", 1)[0]
        if not raw:
            continue
        names.append(raw.decode(encoding, "replace"))

    return names