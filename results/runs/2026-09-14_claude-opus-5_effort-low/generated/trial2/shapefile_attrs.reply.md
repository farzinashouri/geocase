```python
"""Read attribute field names from an ESRI Shapefile.

Shapefile attributes live in the ``.dbf`` sidecar (a dBASE III+/VII table),
so the field names come straight out of that file's header.  Only the
standard library is needed.
"""

from __future__ import annotations

import os

__all__ = ["shapefile_attrs"]

_TERMINATOR = 0x0D
_HEADER_SIZE = 32
_FIELD_DESCRIPTOR_SIZE = 32

# dBASE "language driver" byte (header offset 29) -> Python codec.
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


def _sidecar_path(path, extension):
    """Find a sidecar file next to *path*, tolerating case differences.

    Shapefiles are often shipped with mixed-case extensions (``FOO.SHP`` with
    ``FOO.DBF``), so fall back to a case-insensitive directory scan.
    """
    stem, _ = os.path.splitext(os.fspath(path))
    for candidate in (stem + extension.lower(), stem + extension.upper()):
        if os.path.exists(candidate):
            return candidate

    directory = os.path.dirname(stem) or "."
    wanted = (os.path.basename(stem) + extension).lower()
    try:
        entries = os.listdir(directory)
    except OSError:
        return None
    for entry in entries:
        if entry.lower() == wanted:
            return os.path.join(directory, entry)
    return None


def _encoding(dbf_path, language_driver):
    """Pick the codec for field names: .cpg sidecar, then the driver byte."""
    cpg_path = _sidecar_path(dbf_path, ".cpg")
    if cpg_path is not None:
        try:
            with open(cpg_path, "r", encoding="ascii", errors="ignore") as handle:
                declared = handle.read().strip()
        except OSError:
            declared = ""
        if declared:
            if declared.isdigit():
                declared = "cp" + declared
            try:
                "".encode(declared)
            except LookupError:
                pass
            else:
                return declared

    return _LANGUAGE_DRIVER_CODECS.get(language_driver, "latin-1")


def shapefile_attrs(path):
    """Return the attribute field names of a shapefile, in file order.

    Parameters
    ----------
    path:
        Path to the ``.shp`` file; its ``.dbf`` sidecar must sit alongside it.

    Returns
    -------
    list[str]
        The field names exactly as stored in the table header.
    """
    dbf_path = _sidecar_path(path, ".dbf")
    if dbf_path is None:
        raise FileNotFoundError(
            "no .dbf sidecar found for shapefile: {!r}".format(os.fspath(path))
        )

    with open(dbf_path, "rb") as handle:
        header = handle.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError("truncated .dbf header: {!r}".format(dbf_path))

        header_length = int.from_bytes(header[8:10], "little")
        encoding = _encoding(dbf_path, header[29])

        # Field descriptors run until a 0x0D terminator, and never past the
        # end of the header region.
        descriptors = handle.read(max(header_length - _HEADER_SIZE, 0))

    names = []
    offset = 0
    while offset + _FIELD_DESCRIPTOR_SIZE <= len(descriptors):
        if descriptors[offset] == _TERMINATOR:
            break
        raw = descriptors[offset : offset + 11]
        raw = raw.split(b"\x00", 1)[0]
        names.append(raw.decode(encoding, errors="replace").rstrip(" "))
        offset += _FIELD_DESCRIPTOR_SIZE

    return names
```