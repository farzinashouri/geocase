"""Read attribute field names out of an ESRI Shapefile.

A shapefile's attributes live in the ``.dbf`` sidecar, a dBASE table whose
header is a fixed 32-byte record followed by one 32-byte descriptor per
field, terminated by ``0x0D``.  Parsing that header directly keeps this
module dependency-free and avoids opening the (much larger) geometry file.
"""

from __future__ import annotations

import codecs
import os
import struct

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_FIELD_DESCRIPTOR_SIZE = 32
_FIELD_NAME_SIZE = 11
_FIELD_TERMINATOR = 0x0D
_EOF_MARKER = 0x1A

# dBASE "language driver ID" (header byte 29) -> codec name.  Only the
# values that real-world shapefile writers emit are worth carrying.
_LDID_ENCODINGS = {
    0x01: "cp437", 0x02: "cp850", 0x03: "cp1252", 0x08: "cp865",
    0x09: "cp437", 0x0A: "cp850", 0x0B: "cp437", 0x0D: "cp437",
    0x0E: "cp850", 0x0F: "cp852", 0x10: "cp850", 0x11: "cp437",
    0x12: "cp852", 0x13: "cp932", 0x14: "cp850", 0x15: "cp437",
    0x16: "cp850", 0x17: "cp865", 0x18: "cp437", 0x19: "cp437",
    0x1A: "cp850", 0x1B: "cp437", 0x1C: "cp863", 0x1D: "cp850",
    0x1F: "cp852", 0x22: "cp852", 0x23: "cp852", 0x24: "cp860",
    0x25: "cp850", 0x26: "cp866", 0x37: "cp850", 0x40: "cp852",
    0x4D: "cp936", 0x4E: "cp949", 0x4F: "cp950", 0x50: "cp874",
    0x57: "cp1252", 0x58: "cp1252", 0x59: "cp1252", 0x64: "cp852",
    0x65: "cp866", 0x66: "cp865", 0x67: "cp861", 0x6A: "cp737",
    0x6B: "cp857", 0x78: "cp950", 0x79: "cp949", 0x7A: "cp936",
    0x7B: "cp932", 0x7C: "cp874", 0x7D: "cp1255", 0x7E: "cp1256",
    0x96: "mac_cyrillic", 0x97: "mac_latin2", 0x98: "mac_greek",
    0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253",
    0xCC: "cp1257",
}

# Used when nothing else identifies the code page: it never raises and maps
# bytes 1:1, so names come back exactly as the file stores them.
_FALLBACK_ENCODING = "latin-1"


def shapefile_attrs(path):
    """Return the shapefile's attribute field names, in the order stored.

    Parameters
    ----------
    path:
        Path to the ``.shp`` file (the ``.dbf`` sidecar beside it is what is
        actually read).  Passing the ``.dbf`` directly also works.

    Returns
    -------
    list[str]
        Field names as written in the attribute table.  Geometry is not a
        field, so it is not included; an attribute-less shapefile with only
        the implicit deletion flag yields an empty list.

    Raises
    ------
    FileNotFoundError
        If no ``.dbf`` attribute table can be found for ``path``.
    ValueError
        If the attribute table is truncated or is not a dBASE file.
    """
    path = os.fspath(path)
    if isinstance(path, bytes):
        path = os.fsdecode(path)

    dbf_path = _find_sidecar(path, ".dbf")
    if dbf_path is None:
        raise FileNotFoundError(
            "no .dbf attribute table found alongside {!r}".format(path)
        )

    with open(dbf_path, "rb") as handle:
        header = handle.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(
                "{!r} is too short to be a dBASE table".format(dbf_path)
            )
        header_length = struct.unpack("<H", header[8:10])[0]
        language_driver = header[29]
        # The descriptor array runs to the end of the header.  Some writers
        # leave header_length unset or wrong, so fall back to reading on.
        if header_length > _HEADER_SIZE:
            block = handle.read(header_length - _HEADER_SIZE)
        else:
            block = handle.read()

    encoding = _resolve_encoding(dbf_path, language_driver)

    names = []
    for offset in range(0, len(block), _FIELD_DESCRIPTOR_SIZE):
        descriptor = block[offset:offset + _FIELD_DESCRIPTOR_SIZE]
        if len(descriptor) < _FIELD_DESCRIPTOR_SIZE:
            break
        # 0x0D ends the array; 0x1A/0x00 guard against padded headers
        # (e.g. the Visual FoxPro backlink) being read as fields.
        if descriptor[0] in (_FIELD_TERMINATOR, _EOF_MARKER, 0x00):
            break
        raw = descriptor[:_FIELD_NAME_SIZE].split(b"\x00", 1)[0]
        name = _decode(raw, encoding).rstrip(" ")
        if not name:
            break
        names.append(name)
    return names


def _decode(raw, encoding):
    """Decode a field name, degrading to latin-1 rather than raising."""
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode(_FALLBACK_ENCODING)


def _find_sidecar(path, extension):
    """Locate a sidecar next to ``path``, tolerating case differences."""
    base, own_extension = os.path.splitext(path)
    if own_extension.lower() == extension and os.path.isfile(path):
        return path

    for candidate in (base + extension, base + extension.upper()):
        if os.path.isfile(candidate):
            return candidate

    # Case-insensitive sweep for mixed-case sidecars (Foo.shp / FOO.Dbf) on
    # case-sensitive filesystems.
    directory, stem = os.path.split(base)
    wanted = (stem + extension).lower()
    try:
        entries = os.listdir(directory or os.curdir)
    except OSError:
        return None
    for entry in entries:
        if entry.lower() == wanted:
            candidate = os.path.join(directory, entry)
            if os.path.isfile(candidate):
                return candidate
    return None


def _resolve_encoding(dbf_path, language_driver):
    """Pick a codec: .cpg sidecar first, then the DBF language driver ID."""
    from_cpg = _encoding_from_cpg(dbf_path)
    if from_cpg is not None:
        return from_cpg
    from_ldid = _canonical_codec(_LDID_ENCODINGS.get(language_driver))
    if from_ldid is not None:
        return from_ldid
    return _FALLBACK_ENCODING


def _encoding_from_cpg(dbf_path):
    """Read the optional .cpg sidecar, which names the table's code page."""
    cpg_path = _find_sidecar(dbf_path, ".cpg")
    if cpg_path is None:
        return None
    try:
        with open(cpg_path, "rb") as handle:
            text = handle.read(256).decode("ascii", "ignore")
    except OSError:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    declaration = lines[0].strip('"').strip("'")

    # Values seen in the wild: "UTF-8", "ISO-8859-1", "65001", "ANSI 1252".
    for token in [declaration] + declaration.split():
        codec = _canonical_codec(token)
        if codec is not None:
            return codec
        digits = "".join(char for char in token if char.isdigit())
        if digits:
            if digits == "65001":
                return "utf-8"
            codec = _canonical_codec("cp" + digits)
            if codec is not None:
                return codec
    return None


def _canonical_codec(name):
    """Return the canonical codec name, or None if Python has no such codec."""
    if not name:
        return None
    try:
        return codecs.lookup(name).name
    except (LookupError, TypeError, ValueError):
        return None