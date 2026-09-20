```python
"""Read the attribute field names of an ESRI Shapefile.

A Shapefile stores its attribute table in a ``.dbf`` sidecar (dBASE III+ /
dBASE 7), whose header declares one fixed-size descriptor per field.  Parsing
that header directly keeps this module dependency-free and avoids loading any
record data.

Importing this module has no side effects.
"""

from __future__ import annotations

import codecs
import os
import struct

__all__ = ["shapefile_attrs"]

# --- dBASE III+ / IV / 5 layout -------------------------------------------
_HEADER_LEN = 32          # bytes before the first field descriptor
_FIELD_DESC_LEN = 32      # bytes per field descriptor
_NAME_LEN = 11            # field-name slot, NUL-terminated
_FIELD_TERMINATOR = 0x0D  # marks the end of the descriptor array

# --- dBASE 7 layout (version byte 0x04) -----------------------------------
_D7_VERSION = 0x04
_D7_HEADER_LEN = 68       # 32 standard + 32 language-driver name + 4 reserved
_D7_FIELD_DESC_LEN = 48
_D7_NAME_LEN = 32

# Language driver id (header byte 29) -> Python codec.  Shapefiles in the wild
# lean on this when no .cpg sidecar is present.
_LDID_ENCODINGS = {
    0x01: "cp437", 0x02: "cp850", 0x03: "cp1252", 0x08: "cp865",
    0x09: "cp437", 0x0A: "cp850", 0x0B: "cp437", 0x0D: "cp437",
    0x0E: "cp850", 0x0F: "cp437", 0x10: "cp850", 0x11: "cp437",
    0x12: "cp850", 0x13: "cp932", 0x14: "cp850", 0x15: "cp437",
    0x16: "cp850", 0x17: "cp865", 0x18: "cp437", 0x19: "cp437",
    0x1A: "cp850", 0x1B: "cp437", 0x1C: "cp863", 0x1D: "cp850",
    0x1F: "cp852", 0x22: "cp852", 0x23: "cp852", 0x24: "cp860",
    0x25: "cp850", 0x26: "cp866", 0x37: "cp850", 0x40: "cp852",
    0x4D: "cp936", 0x4E: "cp949", 0x4F: "cp950", 0x50: "cp874",
    0x57: "cp1252", 0x58: "cp1252", 0x59: "cp1252", 0x64: "cp852",
    0x65: "cp866", 0x66: "cp865", 0x67: "cp861", 0x6A: "cp737",
    0x6B: "cp857", 0x6C: "cp863", 0x78: "cp950", 0x79: "cp949",
    0x7A: "cp936", 0x7B: "cp932", 0x7C: "cp874", 0x7D: "cp1255",
    0x7E: "cp1256", 0x96: "mac_cyrillic", 0x97: "mac_latin2",
    0x98: "mac_greek", 0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254",
    0xCB: "cp1253", 0xCC: "cp1257",
}

_FALLBACK_ENCODING = "latin-1"  # total function: never raises on decode


def shapefile_attrs(path):
    """Return the Shapefile's attribute field names, in file order.

    Parameters
    ----------
    path:
        Path to the ``.shp`` (the ``.dbf`` sidecar must sit alongside it).
        A path to the ``.dbf`` itself is also accepted.

    Returns
    -------
    list[str]
        Field names exactly as stored, minus the NUL/space padding the format
        uses to fill the fixed-width name slot.

    Raises
    ------
    FileNotFoundError
        If no ``.dbf`` sidecar can be found next to *path*.
    ValueError
        If the ``.dbf`` header is truncated or malformed.
    """
    dbf_path = _find_sidecar(path, "dbf")
    with open(dbf_path, "rb") as fh:
        header = fh.read(_HEADER_LEN)
        if len(header) < _HEADER_LEN:
            raise ValueError("%s: truncated DBF header" % dbf_path)

        version = header[0] & 0x07
        header_len = struct.unpack("<H", header[8:10])[0]
        if header_len <= _HEADER_LEN:
            raise ValueError("%s: implausible DBF header length %d"
                             % (dbf_path, header_len))

        # The descriptor array runs from the end of the fixed header up to the
        # terminator byte; read the declared header in full and slice it.
        rest = fh.read(header_len - _HEADER_LEN)

    if version == _D7_VERSION:
        desc_start = _D7_HEADER_LEN - _HEADER_LEN
        desc_len, name_len = _D7_FIELD_DESC_LEN, _D7_NAME_LEN
    else:
        desc_start = 0
        desc_len, name_len = _FIELD_DESC_LEN, _NAME_LEN

    encoding = _resolve_encoding(path, header[29])

    names = []
    offset = desc_start
    while offset < len(rest) and rest[offset] != _FIELD_TERMINATOR:
        descriptor = rest[offset:offset + desc_len]
        if len(descriptor) < desc_len:
            raise ValueError("%s: truncated DBF field descriptor" % dbf_path)
        names.append(_decode_name(descriptor[:name_len], encoding))
        offset += desc_len

    if offset >= len(rest):
        raise ValueError("%s: DBF field descriptors are unterminated"
                         % dbf_path)
    return names


def _decode_name(raw, encoding):
    """Decode one fixed-width field-name slot."""
    # The name ends at the first NUL; some writers pad with spaces instead,
    # which shapelib (and therefore GDAL) trims as well.
    raw = raw.split(b"\x00", 1)[0].rstrip(b" ")
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode(_FALLBACK_ENCODING)


def _resolve_encoding(path, ldid):
    """Pick the codec for field names: .cpg sidecar first, then the LDID."""
    try:
        cpg_path = _find_sidecar(path, "cpg")
    except FileNotFoundError:
        cpg_path = None

    if cpg_path is not None:
        with open(cpg_path, "rb") as fh:
            declared = fh.read(64).decode(_FALLBACK_ENCODING).strip()
        encoding = _normalize_cpg(declared)
        if encoding is not None:
            return encoding

    return _LDID_ENCODINGS.get(ldid, _FALLBACK_ENCODING)


def _normalize_cpg(declared):
    """Map a .cpg body to a Python codec name, or None if unusable."""
    if not declared:
        return None

    # ArcGIS writes forms like "UTF-8", "ISO-8859-1", "65001", "LDID/87".
    if declared.upper().startswith("LDID/"):
        try:
            return _LDID_ENCODINGS.get(int(declared[5:]))
        except ValueError:
            return None

    candidates = [declared]
    if declared.isdigit():
        candidates.insert(0, "cp" + declared)
        if declared == "65001":
            candidates.insert(0, "utf-8")

    for candidate in candidates:
        try:
            codecs.lookup(candidate)
        except LookupError:
            continue
        return candidate
    return None


def _find_sidecar(path, ext):
    """Locate the sidecar with extension *ext* next to a Shapefile *path*.

    Shapefile sidecars are frequently mixed-case (``FOO.DBF`` beside
    ``foo.shp``), so fall back to a case-insensitive directory scan on
    case-sensitive filesystems.
    """
    path = os.fspath(path)
    base = os.path.splitext(path)[0]

    for candidate in (base + "." + ext.lower(), base + "." + ext.upper()):
        if os.path.isfile(candidate):
            return candidate

    directory = os.path.dirname(base) or os.curdir
    wanted = os.path.basename(base).lower() + "." + ext.lower()
    try:
        entries = os.listdir(directory)
    except OSError:
        entries = []
    for entry in entries:
        if entry.lower() == wanted:
            candidate = os.path.join(directory, entry)
            if os.path.isfile(candidate):
                return candidate

    raise FileNotFoundError(
        "no .%s sidecar found for %s" % (ext.lower(), path)
    )
```