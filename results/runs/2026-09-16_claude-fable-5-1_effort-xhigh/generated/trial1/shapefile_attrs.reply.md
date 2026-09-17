Every attempt to run Python or write scratch files was denied by the sandbox, so I could not execute the module. I did read the raw DBF headers of the repo's two shapefile test cases and hand-traced the parser against them: the legacy-encoding file yields `city`, `country`, and the truncation file yields `temperatur`, `temperat_1`, `precipitat`, `wind_speed`, matching what those files store.

```python
"""Read the attribute field names of an ESRI Shapefile.

A shapefile's attribute table is its ``.dbf`` sidecar (dBASE III/IV layout).
The field names live in the DBF header, so they are recovered by parsing that
header directly with the standard library; the geometry is never touched.
"""

from __future__ import annotations

import codecs
import os
import re
import struct

__all__ = ["shapefile_attrs"]

_DBF_FIXED_HEADER = 32  # bytes before the first field descriptor
_FIELD_DESCRIPTOR = 32  # bytes per field descriptor
_FIELD_NAME_BYTES = 11  # name slot inside a descriptor (10 chars + NUL)
_FIELD_TERMINATOR = 0x0D  # single byte closing the descriptor array
_LDID_OFFSET = 29  # header byte holding the dBASE "language driver ID"

# Language driver ID -> code page, mirroring the table GDAL/shapelib use.
# IDs whose code page has no Python codec are left out.
_LDID_CODEPAGES = {
    0x01: 437, 0x02: 850, 0x03: 1252, 0x04: 10000, 0x08: 865, 0x09: 437,
    0x0A: 850, 0x0B: 437, 0x0D: 437, 0x0E: 850, 0x0F: 437, 0x10: 850,
    0x11: 437, 0x12: 850, 0x13: 932, 0x14: 850, 0x15: 437, 0x16: 850,
    0x17: 865, 0x18: 437, 0x19: 437, 0x1A: 850, 0x1B: 437, 0x1C: 863,
    0x1D: 850, 0x1F: 852, 0x22: 852, 0x23: 852, 0x24: 860, 0x25: 850,
    0x26: 866, 0x37: 850, 0x40: 852, 0x4D: 936, 0x4E: 949, 0x4F: 950,
    0x50: 874, 0x57: 1252, 0x58: 1252, 0x59: 1252, 0x64: 852, 0x65: 866,
    0x66: 865, 0x67: 861, 0x6A: 737, 0x6B: 857, 0x6C: 863, 0x78: 950,
    0x79: 949, 0x7A: 936, 0x7B: 932, 0x7C: 874, 0x7D: 1255, 0x7E: 1256,
    0x86: 737, 0x87: 852, 0x88: 857, 0xC8: 1250, 0xC9: 1251, 0xCA: 1254,
    0xCB: 1253, 0xCC: 1257,
}

# Spellings seen in .cpg files that ``codecs.lookup`` does not accept as-is.
_CPG_CODEPAGE_NUMBER = re.compile(r"^(?:ANSI|OEM|CP|WINDOWS|MS)?[\s_-]*(\d{3,5})$", re.I)
_CPG_LDID = re.compile(r"^LDID[/\s_-]*(\d{1,3})$", re.I)
_CPG_ISO_8859 = re.compile(r"^ISO[\s_-]*8859[\s_-]*(\d{1,2})$", re.I)


def shapefile_attrs(path: str | os.PathLike[str]) -> list[str]:
    """Return the attribute field names of the shapefile at ``path``.

    ``path`` normally points at the ``.shp`` file; the ``.dbf`` (and optional
    ``.cpg``) sidecars are located next to it by shared basename, matching the
    extension case-insensitively.  Names come back in file order, exactly as
    stored: no case folding, no renaming, no de-duplication.  A shapefile whose
    attribute table declares no fields yields an empty list.

    Raises ``FileNotFoundError`` if no ``.dbf`` accompanies the shapefile and
    ``ValueError`` if the ``.dbf`` header is unreadable.
    """
    shp = os.fsdecode(path)
    dbf = _sidecar(shp, ".dbf")
    if dbf is None:
        raise FileNotFoundError(f"No .dbf attribute table found alongside {shp!r}")

    ldid, raw_names = _read_dbf_field_names(dbf)
    encodings = _candidate_encodings(_sidecar(shp, ".cpg"), ldid)
    return [_decode(raw, encodings) for raw in raw_names]


def _sidecar(path: str, ext: str) -> str | None:
    """Locate ``<stem><ext>`` next to ``path``, tolerating extension case."""
    stem, _ = os.path.splitext(path)
    for candidate in (stem + ext, stem + ext.upper()):
        if os.path.isfile(candidate):
            return candidate

    directory, base = os.path.split(stem)
    wanted = (base + ext).lower()
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


def _read_dbf_field_names(dbf_path: str) -> tuple[int, list[bytes]]:
    """Parse the DBF header; return the language driver ID and raw names."""
    with open(dbf_path, "rb") as fh:
        fixed = fh.read(_DBF_FIXED_HEADER)
        if len(fixed) < _DBF_FIXED_HEADER:
            raise ValueError(f"{dbf_path!r} is too short to be a DBF file")
        header_len = struct.unpack_from("<H", fixed, 8)[0]
        ldid = fixed[_LDID_OFFSET]

        # The descriptor array normally ends with 0x0D, but some writers omit
        # it, so also cap the count by the declared header length.  FoxPro
        # pads the header after the terminator, so the cap alone is not
        # enough either; a nonsensical header length disables the cap.
        max_fields = None
        if header_len >= _DBF_FIXED_HEADER:
            max_fields = (header_len - _DBF_FIXED_HEADER) // _FIELD_DESCRIPTOR

        names: list[bytes] = []
        while max_fields is None or len(names) < max_fields:
            descriptor = fh.read(_FIELD_DESCRIPTOR)
            if len(descriptor) < _FIELD_DESCRIPTOR or descriptor[0] == _FIELD_TERMINATOR:
                break
            # The slot is NUL-terminated and NUL-padded; a few writers pad with
            # spaces instead, which shapelib also strips.
            name = descriptor[:_FIELD_NAME_BYTES].split(b"\x00", 1)[0]
            names.append(name.rstrip(b" "))
    return ldid, names


def _candidate_encodings(cpg_path: str | None, ldid: int) -> list[str]:
    """Codecs to try in order: the .cpg declaration, strict UTF-8, the header's
    language driver ID, then cp1252 as the de-facto legacy default."""
    candidates: list[str] = []
    if cpg_path is not None:
        declared = _codec_from_cpg(cpg_path)
        if declared is not None:
            candidates.append(declared)
    candidates.append("utf-8")
    codepage = _LDID_CODEPAGES.get(ldid)
    if codepage is not None:
        candidates.append(_codepage_codec(codepage))
    candidates.append("cp1252")
    return candidates


def _codepage_codec(codepage: int) -> str:
    return "mac_roman" if codepage == 10000 else f"cp{codepage}"


def _codec_from_cpg(cpg_path: str) -> str | None:
    """Read a .cpg file and translate its contents to a Python codec name."""
    try:
        with open(cpg_path, "rb") as fh:
            text = fh.read(256).decode("ascii", "ignore")
    except OSError:
        return None
    lines = text.strip().splitlines()
    declared = lines[0].strip() if lines else ""
    if not declared:
        return None

    candidates = [declared]
    match = _CPG_LDID.match(declared)
    if match:
        codepage = _LDID_CODEPAGES.get(int(match.group(1)))
        if codepage is not None:
            candidates.append(_codepage_codec(codepage))
    match = _CPG_CODEPAGE_NUMBER.match(declared)
    if match:
        candidates.append(_codepage_codec(int(match.group(1))))
    match = _CPG_ISO_8859.match(declared)
    if match:
        candidates.append(f"iso8859-{match.group(1)}")

    for name in candidates:
        try:
            return codecs.lookup(name).name
        except LookupError:
            continue
    return None


def _decode(raw: bytes, encodings: list[str]) -> str:
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1")  # never fails; keeps every byte as a char
```