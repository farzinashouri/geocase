```python
"""Read the attribute field names of an ESRI Shapefile.

A Shapefile keeps its attribute table in the ``.dbf`` sidecar, an xBase/dBASE
file.  Field names live in the DBF header, so only that header is read; the
``.shp`` geometry file itself is never opened.  Names are returned in file
order, decoded with the encoding the dataset declares (``.cpg`` sidecar first,
then the DBF language-driver byte), falling back to UTF-8 and finally Latin-1
so that decoding can never fail.
"""

from __future__ import annotations

import codecs
import os
import re
import struct

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32          # fixed DBF file header, field descriptors follow it
_FIELD_TERMINATOR = 0x0D   # byte that ends the field-descriptor array
_MAX_HEADER_BYTES = 4 * 1024 * 1024  # guard against corrupt header lengths

# dBASE "language driver ID" (header byte 29) -> Python codec name.
_LDID_CODEPAGES = {
    0x01: "cp437", 0x02: "cp850", 0x03: "cp1252", 0x04: "mac_roman",
    0x08: "cp865", 0x09: "cp437", 0x0A: "cp850", 0x0B: "cp437",
    0x0D: "cp437", 0x0E: "cp850", 0x0F: "cp437", 0x10: "cp850",
    0x11: "cp437", 0x12: "cp850", 0x13: "cp932", 0x14: "cp850",
    0x15: "cp437", 0x16: "cp850", 0x17: "cp865", 0x18: "cp437",
    0x19: "cp437", 0x1A: "cp850", 0x1B: "cp437", 0x1C: "cp863",
    0x1D: "cp850", 0x1F: "cp852", 0x22: "cp852", 0x23: "cp852",
    0x24: "cp860", 0x25: "cp850", 0x26: "cp866", 0x37: "cp850",
    0x40: "cp852", 0x4D: "cp936", 0x4E: "cp949", 0x4F: "cp950",
    0x50: "cp874", 0x57: "cp1252", 0x58: "cp1252", 0x59: "cp1252",
    0x64: "cp852", 0x65: "cp866", 0x66: "cp865", 0x67: "cp861",
    0x6A: "cp737", 0x6B: "cp857", 0x6C: "cp863", 0x78: "cp950",
    0x79: "cp949", 0x7A: "cp936", 0x7B: "cp932", 0x7C: "cp874",
    0x7D: "cp1255", 0x7E: "cp1256", 0x86: "cp737", 0x87: "cp852",
    0x88: "cp857", 0x96: "mac_cyrillic", 0x97: "mac_latin2",
    0x98: "mac_greek", 0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254",
    0xCB: "cp1253", 0xCC: "cp1257",
}


def _find_sidecar(path: str, ext: str) -> str | None:
    """Locate ``<stem><ext>`` next to *path*, tolerating a differently cased extension."""
    root, _ = os.path.splitext(path)
    for candidate in (root + ext, root + ext.upper()):
        if os.path.isfile(candidate):
            return candidate
    directory, stem = os.path.split(root)
    try:
        entries = os.listdir(directory or os.curdir)
    except OSError:
        return None
    for entry in entries:
        entry_root, entry_ext = os.path.splitext(entry)
        if entry_root == stem and entry_ext.lower() == ext:
            candidate = os.path.join(directory, entry)
            if os.path.isfile(candidate):
                return candidate
    return None


def _codec_or_none(name: str) -> str | None:
    """Return the canonical codec name if Python knows *name*, else ``None``."""
    try:
        return codecs.lookup(name).name
    except (LookupError, TypeError, ValueError):
        return None


def _encoding_from_cpg(text: str) -> str | None:
    """Translate the contents of a ``.cpg`` sidecar into a Python codec name.

    ``.cpg`` files are free-form: ``UTF-8``, ``ISO-8859-1``, ``88591``,
    ``ANSI 1252``, ``OEM 850``, ``1252``, ``LDID/87`` and similar all occur.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    value = lines[0]

    if value.upper().startswith("LDID/"):
        try:
            ldid = int(value[5:].strip())
        except ValueError:
            return None
        enc = _LDID_CODEPAGES.get(ldid)
        return _codec_or_none(enc) if enc else None

    compact = re.sub(r"[\s_\-]+", "", value).upper()
    candidates = [value]
    match = re.fullmatch(r"(?:ISO)?8859(\d{1,2})", compact)
    if match:
        candidates.append("iso-8859-" + match.group(1))
    match = re.fullmatch(r"(?:ANSI|OEM|CP|WINDOWS|WIN|IBM|MS)?(\d{3,5})", compact)
    if match:
        candidates.append("cp" + match.group(1))
    candidates.append(compact)

    for candidate in candidates:
        codec = _codec_or_none(candidate)
        if codec:
            return codec
    return None


def _decode(raw: bytes, encodings: list[str]) -> str:
    """Decode *raw* with the first encoding that succeeds; Latin-1 never fails."""
    for enc in encodings:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1")


def shapefile_attrs(path) -> list[str]:
    """Return the attribute field names of the Shapefile at *path*, in file order.

    *path* normally points at the ``.shp`` file; the ``.dbf`` sidecar (any
    extension case) is located next to it.  Pointing directly at the ``.dbf``
    also works.  Names are returned exactly as stored: no case folding,
    no truncation beyond what the file itself did, and no reordering.

    Raises ``FileNotFoundError`` if no ``.dbf`` sidecar exists and
    ``ValueError`` if the file is too short to hold a DBF header.
    """
    path = os.fspath(path)
    if isinstance(path, bytes):
        path = os.fsdecode(path)

    dbf_path = _find_sidecar(path, ".dbf")
    if dbf_path is None:
        raise FileNotFoundError(f"No .dbf attribute table found alongside {path!r}")

    with open(dbf_path, "rb") as fh:
        head = fh.read(_HEADER_SIZE)
        if len(head) < _HEADER_SIZE:
            raise ValueError(f"{dbf_path!r} is too short to be a DBF file")
        header_len = struct.unpack_from("<H", head, 8)[0]
        if header_len > _HEADER_SIZE:
            body = fh.read(min(header_len - _HEADER_SIZE, _MAX_HEADER_BYTES))
        else:
            # Corrupt/zero header length: read a bounded chunk and rely on
            # the 0x0D terminator instead.
            body = fh.read(_MAX_HEADER_BYTES)
    header = head + body

    version = head[0]
    ldid = head[29]

    # dBASE 7 uses 48-byte descriptors with 32-byte names; everything else
    # (dBASE III/IV, FoxPro, Visual FoxPro) uses 32-byte descriptors with
    # 11-byte names.  Shapefiles are almost always the latter.
    if (version & 0x07) == 4:
        desc_size, name_size = 48, 32
    else:
        desc_size, name_size = 32, 11

    limit = min(len(header), header_len) if header_len > _HEADER_SIZE else len(header)

    raw_names: list[bytes] = []
    pos = _HEADER_SIZE
    while pos < limit and header[pos] != _FIELD_TERMINATOR:
        if pos + name_size > len(header):
            break
        name_field = header[pos:pos + name_size]
        # Names are NUL-terminated; some writers pad with spaces instead.
        raw_names.append(name_field.split(b"\x00", 1)[0].rstrip(b" "))
        pos += desc_size

    encodings: list[str] = []
    cpg_path = _find_sidecar(path, ".cpg")
    if cpg_path is not None:
        try:
            with open(cpg_path, "rb") as fh:
                cpg_text = fh.read(256).decode("ascii", "ignore")
        except OSError:
            cpg_text = ""
        cpg_enc = _encoding_from_cpg(cpg_text)
        if cpg_enc:
            encodings.append(cpg_enc)
    ldid_enc = _LDID_CODEPAGES.get(ldid)
    if ldid_enc and _codec_or_none(ldid_enc):
        encodings.append(ldid_enc)
    encodings.append("utf-8")

    return [_decode(raw, encodings) for raw in raw_names]
```