"""Read the attribute field names of an ESRI Shapefile.

A shapefile stores its attribute table in a sidecar ``.dbf`` file (dBASE
format).  The field names live in the ``.dbf`` header, so they can be read
without pulling in a vector I/O library: the header is a small, fully
specified binary structure.

Only the standard library is used.
"""

from __future__ import annotations

import os
import struct

__all__ = ["shapefile_attrs", "ShapefileError"]


class ShapefileError(Exception):
    """Raised when the shapefile or its .dbf sidecar cannot be read."""


# dBASE "language driver ID" (byte 29 of the header) -> Python codec.
# Only the values that show up in practice are listed; anything else falls
# back to latin-1, which never fails and round-trips the raw bytes.
_LDID_CODECS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
    0x04: "mac-roman",
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


def shapefile_attrs(path):
    """Return the shapefile's attribute field names, in file order.

    Parameters
    ----------
    path :
        Path to the ``.shp`` file (or directly to its ``.dbf`` sidecar).
        The usual sidecar files are expected to sit next to it.

    Returns
    -------
    list of str
        The attribute field names exactly as stored in the file, in the
        order the attribute table declares them.  A shapefile with no
        attribute fields yields an empty list.

    Raises
    ------
    ShapefileError
        If the ``.dbf`` sidecar is missing or its header is malformed.
    """
    dbf_path = _find_dbf(path)

    with open(dbf_path, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ShapefileError("truncated .dbf header: %s" % (dbf_path,))

        version = header[0]
        header_length = struct.unpack("<H", header[8:10])[0]
        ldid = header[29]

        # dBASE 7 ("level 7") widens the field descriptor from 32 to 48
        # bytes and the field name from 11 to 32 bytes.
        if version & 0x07 == 0x04:
            descriptor_size, name_size = 48, 32
        else:
            descriptor_size, name_size = 32, 11

        # The descriptor array runs from the end of the 32-byte header up to
        # a 0x0D terminator; header_length bounds it but is not always exact,
        # so treat it as an upper bound only.
        remaining = max(header_length - 32, 0)
        descriptors = fh.read(remaining) if remaining else fh.read()

    encoding = _resolve_encoding(dbf_path, ldid)

    names = []
    offset = 0
    while offset + descriptor_size <= len(descriptors):
        chunk = descriptors[offset:offset + descriptor_size]
        if chunk[0] == _FIELD_TERMINATOR:
            break
        raw = chunk[:name_size].split(b"\x00", 1)[0]
        names.append(raw.decode(encoding, errors="replace").strip())
        offset += descriptor_size

    return names


def _find_dbf(path):
    """Locate the .dbf sidecar for *path*, tolerating extension casing."""
    path = os.fspath(path)
    stem, ext = os.path.splitext(path)

    if ext.lower() == ".dbf" and os.path.exists(path):
        return path

    candidates = [stem + ".dbf", stem + ".DBF", stem + ".Dbf"]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    # Last resort: a case-insensitive scan of the containing directory, for
    # filesystems that preserve odd casing we did not guess above.
    directory = os.path.dirname(stem) or "."
    wanted = os.path.basename(stem).lower() + ".dbf"
    try:
        entries = os.listdir(directory)
    except OSError:
        entries = []
    for entry in entries:
        if entry.lower() == wanted:
            return os.path.join(directory, entry)

    raise ShapefileError("no .dbf sidecar found for %s" % (path,))


def _resolve_encoding(dbf_path, ldid):
    """Pick a codec for field names: .cpg sidecar first, then the LDID byte."""
    declared = _read_cpg(dbf_path)
    if declared:
        for candidate in (declared, "cp" + declared.lstrip("0")):
            if _codec_exists(candidate):
                return candidate

    codec = _LDID_CODECS.get(ldid)
    if codec and _codec_exists(codec):
        return codec

    # latin-1 decodes any byte sequence, so names survive verbatim.
    return "latin-1"


def _read_cpg(dbf_path):
    """Return the code page named by the .cpg sidecar, or None."""
    stem = os.path.splitext(dbf_path)[0]
    for candidate in (stem + ".cpg", stem + ".CPG", stem + ".cst"):
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "rb") as fh:
                text = fh.read(256).decode("ascii", errors="ignore").strip()
        except OSError:
            return None
        return text or None
    return None


def _codec_exists(name):
    try:
        "".encode(name)
    except (LookupError, TypeError, ValueError):
        return False
    return True