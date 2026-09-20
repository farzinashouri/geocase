"""Read ESRI Shapefile attribute field names without a vector I/O library.

A shapefile's attribute table lives in its ``.dbf`` sidecar (dBASE III+ /
dBASE 7 format).  The field names are stored in fixed-width field descriptors
in the ``.dbf`` header, so they can be recovered by parsing that header
directly with the standard library.

Importing this module has no side effects.
"""

from __future__ import annotations

import os
import struct

__all__ = ["shapefile_attrs"]

# Field-descriptor layout differs between dBASE III+/IV/V/FoxPro and dBASE 7.
_DESCRIPTOR_SIZE = 32
_NAME_SIZE = 11  # 10 significant characters + NUL terminator
_DESCRIPTOR_SIZE_DBASE7 = 48
_NAME_SIZE_DBASE7 = 32

_HEADER_TERMINATORS = (0x0D, 0x1A)

# Language driver IDs (byte 29 of the header) seen in the wild, mapped to
# Python codec names.  Anything unlisted falls back to a byte-preserving codec.
_LDID_CODECS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
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

_FALLBACK_CODEC = "latin-1"


def shapefile_attrs(path):
    """Return the attribute field names of a shapefile, in file order.

    Parameters
    ----------
    path : str | os.PathLike
        Path to the ``.shp`` file (its ``.dbf`` sidecar must sit alongside it).
        A path to the ``.dbf`` itself is also accepted.

    Returns
    -------
    list[str]
        Field names exactly as stored in the attribute table, in declaration
        order.  A table with no attribute fields yields an empty list.

    Raises
    ------
    FileNotFoundError
        If no ``.dbf`` sidecar can be located next to *path*.
    ValueError
        If the ``.dbf`` header is truncated or malformed.
    """
    dbf_path = _find_dbf(path)
    with open(dbf_path, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError(f"truncated DBF header: {dbf_path!s}")

        version = header[0]
        ldid = header[29]
        # Bytes 8-9 hold the total header length; it bounds the descriptor area.
        header_length = struct.unpack("<H", header[8:10])[0]

        if (version & 0x07) == 0x04:  # dBASE 7 ("Level 7") table
            descriptor_size = _DESCRIPTOR_SIZE_DBASE7
            name_size = _NAME_SIZE_DBASE7
        else:
            descriptor_size = _DESCRIPTOR_SIZE
            name_size = _NAME_SIZE

        descriptor_bytes = max(header_length - 32, 0)
        raw = fh.read(descriptor_bytes) if descriptor_bytes else fh.read()

    codec = _resolve_codec(dbf_path, ldid)

    names = []
    for offset in range(0, len(raw), descriptor_size):
        chunk = raw[offset : offset + descriptor_size]
        if not chunk or chunk[0] in _HEADER_TERMINATORS:
            break
        if len(chunk) < name_size:
            break
        name = _decode_name(chunk[:name_size], codec)
        if name:
            names.append(name)
    return names


def _find_dbf(path):
    """Locate the ``.dbf`` sidecar for *path*, tolerating extension casing."""
    text = os.fspath(path)
    stem, ext = os.path.splitext(text)
    if ext.lower() == ".dbf" and os.path.exists(text):
        return text

    candidates = [stem + suffix for suffix in (".dbf", ".DBF", ".Dbf")]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    # Fall back to a case-insensitive scan of the containing directory, which
    # covers oddly-cased sidecars on case-sensitive filesystems.
    directory = os.path.dirname(stem) or "."
    wanted = os.path.basename(stem).lower() + ".dbf"
    try:
        entries = os.listdir(directory)
    except OSError:
        entries = []
    for entry in entries:
        if entry.lower() == wanted:
            return os.path.join(directory, entry)

    raise FileNotFoundError(f"no .dbf sidecar found for {text!r}")


def _resolve_codec(dbf_path, ldid):
    """Pick a codec for field names from the ``.cpg`` sidecar, else the LDID."""
    for codec in (_read_cpg(dbf_path), _LDID_CODECS.get(ldid)):
        if codec and _codec_exists(codec):
            return codec
    return _FALLBACK_CODEC


def _read_cpg(dbf_path):
    """Return the codec named by the ``.cpg`` sidecar, or ``None``."""
    stem = os.path.splitext(os.fspath(dbf_path))[0]
    for suffix in (".cpg", ".CPG", ".cst", ".CST"):
        candidate = stem + suffix
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "rb") as fh:
                text = fh.read(64).decode("ascii", "ignore").strip()
        except OSError:
            return None
        if not text:
            return None
        if text.isdigit():  # e.g. "65001" or "1252" (a Windows code page)
            number = int(text)
            return "utf-8" if number == 65001 else f"cp{number}"
        return text
    return None


def _codec_exists(name):
    try:
        "".encode(name)
    except LookupError:
        return False
    except Exception:
        return False
    return True


def _decode_name(raw_name, codec):
    """Decode one field name: NUL-terminated, space-padded by some writers."""
    terminator = raw_name.find(b"\x00")
    if terminator != -1:
        raw_name = raw_name[:terminator]
    try:
        name = raw_name.decode(codec)
    except (UnicodeDecodeError, LookupError):
        name = raw_name.decode(_FALLBACK_CODEC)
    return name.rstrip(" ")