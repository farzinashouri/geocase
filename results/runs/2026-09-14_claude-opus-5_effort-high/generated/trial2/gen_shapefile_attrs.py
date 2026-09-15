"""Read the attribute field names of an ESRI Shapefile.

A shapefile stores its attribute table in a dBASE (``.dbf``) sidecar file, so the
field names live in that file's header rather than in the ``.shp`` geometry file.
This module parses that header directly with the standard library.
"""

from __future__ import annotations

import codecs
import struct
from pathlib import Path

__all__ = ["shapefile_attrs"]

_HEADER_SIZE = 32
_FIELD_TERMINATOR = 0x0D

# Standard dBASE field descriptors are 32 bytes with an 11-byte name; dBASE
# level 7 (version nibble 4) widens them to 48 bytes with a 32-byte name.
_DBASE7_VERSION = 0x04

# dBASE "language driver ID" (header byte 29) -> Python codec, for the common
# code pages emitted by GIS software.
_LDID_CODECS = {
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
    0x7D: "cp1255", 0x7E: "cp1256", 0x96: "mac_cyrillic",
    0x97: "mac_latin2", 0x98: "mac_greek", 0xC8: "cp1250",
    0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253", 0xCC: "cp1257",
}

# Used when the file declares no code page. Field names are ASCII by
# specification, and this decodes any byte without raising.
_FALLBACK_CODEC = "cp1252"


def shapefile_attrs(path) -> list[str]:
    """Return the attribute field names of a shapefile, in file order.

    Args:
        path: Path to the ``.shp`` file; its sidecars must sit alongside it.

    Returns:
        The field names exactly as stored, in their declared order. A shapefile
        whose attribute table holds only the implicit geometry record returns an
        empty list.

    Raises:
        FileNotFoundError: If the ``.dbf`` sidecar is missing.
        ValueError: If the ``.dbf`` header is truncated or malformed.
    """
    shp_path = Path(path)
    dbf_path = _find_sidecar(shp_path, ".dbf")
    if dbf_path is None:
        raise FileNotFoundError(
            f"no .dbf attribute table found alongside {shp_path}"
        )

    version, ldid, descriptors = _read_dbf_header(dbf_path)
    encoding = _resolve_encoding(shp_path, ldid)
    return _parse_field_names(descriptors, version, encoding)


def _find_sidecar(shp_path: Path, suffix: str) -> Path | None:
    """Locate a sidecar file, tolerating upper/mixed-case extensions."""
    candidate = shp_path.with_suffix(suffix)
    if candidate.is_file():
        return candidate

    wanted = candidate.name.lower()
    try:
        entries = list(shp_path.parent.iterdir())
    except OSError:
        return None
    for entry in entries:
        if entry.name.lower() == wanted and entry.is_file():
            return entry
    return None


def _read_dbf_header(dbf_path: Path) -> tuple[int, int, bytes]:
    """Return (version byte, language driver id, field descriptor bytes)."""
    with dbf_path.open("rb") as handle:
        header = handle.read(_HEADER_SIZE)
        if len(header) < _HEADER_SIZE:
            raise ValueError(f"{dbf_path} is too short to be a dBASE file")

        version = header[0]
        ldid = header[29]
        header_length = struct.unpack_from("<H", header, 8)[0]

        if header_length > _HEADER_SIZE:
            descriptors = handle.read(header_length - _HEADER_SIZE)
        else:
            # Header length is unset or nonsensical; read enough to cover the
            # 255-field maximum and rely on the terminator byte instead.
            descriptors = handle.read(255 * 48 + 1)

    return version, ldid, descriptors


def _parse_field_names(
    descriptors: bytes, version: int, encoding: str
) -> list[str]:
    """Walk the fixed-width field descriptors until the terminator byte."""
    if (version & 0x07) == _DBASE7_VERSION:
        descriptor_size, name_size = 48, 32
    else:
        descriptor_size, name_size = 32, 11

    names: list[str] = []
    offset = 0
    while offset + descriptor_size <= len(descriptors):
        if descriptors[offset] == _FIELD_TERMINATOR:
            return names
        raw = descriptors[offset:offset + name_size]
        names.append(_decode_name(raw, encoding))
        offset += descriptor_size

    # Some writers omit the terminator; a partial trailing descriptor, though,
    # means the header was cut short.
    if offset != len(descriptors):
        raise ValueError("truncated dBASE field descriptor in header")
    return names


def _decode_name(raw: bytes, encoding: str) -> str:
    """Decode one null-terminated, blank-padded field name."""
    trimmed = raw.split(b"\x00", 1)[0].strip(b" \t")
    try:
        return trimmed.decode(encoding)
    except UnicodeDecodeError:
        return trimmed.decode("latin-1")


def _resolve_encoding(shp_path: Path, ldid: int) -> str:
    """Prefer the .cpg sidecar, then the header's language driver id."""
    cpg_path = _find_sidecar(shp_path, ".cpg")
    if cpg_path is not None:
        try:
            declared = cpg_path.read_bytes().decode("ascii", "ignore")
        except OSError:
            declared = ""
        encoding = _normalize_codec(declared)
        if encoding is not None:
            return encoding

    return _LDID_CODECS.get(ldid, _FALLBACK_CODEC)


def _normalize_codec(declared: str) -> str | None:
    """Map a .cpg file's contents onto a Python codec name, if it names one."""
    text = declared.strip().splitlines()[0].strip() if declared.strip() else ""
    if not text:
        return None

    # Entries such as "ANSI 1252" or "UTF 8" carry the code page in the tail.
    tokens = text.split()
    if len(tokens) > 1 and tokens[-1].isdigit():
        text = tokens[-1]

    candidates = [text]
    if text.isdigit():
        code = int(text)
        if code == 65001:
            candidates = ["utf-8"]
        elif code == 65000:
            candidates = ["utf-7"]
        elif code == 10000:
            candidates = ["mac_roman"]
        else:
            candidates = [f"cp{code}"]

    for candidate in candidates:
        try:
            return codecs.lookup(candidate).name
        except LookupError:
            continue
    return None