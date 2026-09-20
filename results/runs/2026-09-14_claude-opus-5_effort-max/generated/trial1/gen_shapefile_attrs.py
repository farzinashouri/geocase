"""Read the attribute field names of an ESRI Shapefile.

A shapefile stores its attribute table in the ``.dbf`` sidecar that sits
next to the ``.shp``.  The field names live in that file's fixed-size
dBASE header, ahead of any record data, so they can be read with nothing
but the standard library -- no geometry is parsed and the records are
never touched.
"""

from __future__ import annotations

import codecs
import os
import re
from pathlib import Path

__all__ = ["shapefile_attrs"]

# Extensions we strip off the caller's path before looking for siblings, so
# that "roads.shp", "roads.dbf" and plain "roads" all resolve to the same set.
_SIDECAR_SUFFIXES = frozenset({".shp", ".shx", ".dbf", ".cpg", ".prj", ".sbn", ".sbx"})

# dBASE table layout.  ESRI writes shapefile attributes as dBASE III/IV, whose
# header is 32 bytes followed by one 32-byte descriptor per field and a
# terminator byte.  Field names occupy the first 11 bytes of a descriptor and
# are NUL-padded.
_TABLE_HEADER_SIZE = 32
_FIELD_DESCRIPTOR_SIZE = 32
_FIELD_NAME_SIZE = 11
_FIELD_TERMINATOR = 0x0D
_HEADER_SIZE_RANGE = slice(8, 10)
_LDID_OFFSET = 29

# Language driver ID (header byte 29) -> Python codec.  Values without a
# stdlib codec (0x68 cp895, 0x69 cp620) are deliberately absent.
_LDID_ENCODINGS = {
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
    0x6A: "cp737", 0x6B: "cp857", 0x78: "cp950", 0x79: "cp949",
    0x7A: "cp936", 0x7B: "cp932", 0x7C: "cp874", 0x7D: "cp1255",
    0x7E: "cp1256", 0x86: "cp737", 0x87: "cp852", 0x88: "cp857",
    0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253",
    0xCC: "cp1257",
}

# Numeric code pages a .cpg file may name that are not spelled "cp<n>".
_CODE_PAGE_ALIASES = {65001: "utf-8", 65000: "utf-7", 1200: "utf-16-le", 1201: "utf-16-be"}

_LDID_TAG = re.compile(r"\ALDID/([0-9]+)\Z", re.IGNORECASE)
_CPG_TOKEN = re.compile(r"[A-Za-z0-9._/-]+")


def shapefile_attrs(path: str | os.PathLike[str]) -> list[str]:
    """Return a shapefile's attribute field names, in the order it stores them.

    ``path`` is the ``.shp`` file; its sidecars are expected alongside it.
    The ``.dbf`` or the extensionless base path is accepted too.  Names are
    returned verbatim -- case and spelling are untouched, with only the
    header's NUL/space padding removed.

    >>> shapefile_attrs("ne_110m_admin_0_countries.shp")  # doctest: +SKIP
    ['featurecla', 'scalerank', 'LABELRANK', 'SOVEREIGNT', ...]

    Raises ``FileNotFoundError`` if no ``.dbf`` sits next to ``path``, and
    ``ValueError`` if that file's header is not a readable dBASE table.
    """
    dbf_path = _find_dbf(Path(path))
    header = _read_table_header(dbf_path)
    encodings = _candidate_encodings(dbf_path, header[_LDID_OFFSET])

    names: list[str] = []
    offset = _TABLE_HEADER_SIZE
    while offset < len(header):
        if header[offset] == _FIELD_TERMINATOR:
            break
        if offset + _FIELD_DESCRIPTOR_SIZE > len(header):
            raise ValueError(f"{dbf_path}: truncated dBASE field descriptor")
        raw = header[offset:offset + _FIELD_NAME_SIZE].split(b"\x00", 1)[0]
        names.append(_decode(raw, encodings).rstrip(" "))
        offset += _FIELD_DESCRIPTOR_SIZE
    return names


def _find_dbf(source: Path) -> Path:
    dbf_path = _sidecar(source, "dbf")
    if dbf_path is None:
        raise FileNotFoundError(f"no .dbf attribute table alongside {source}")
    return dbf_path


def _sidecar(source: Path, extension: str) -> Path | None:
    """Locate the sibling file with ``extension``, matched case-insensitively.

    Shapefiles are routinely shipped with upper-case sidecars, which only
    resolve for free on case-insensitive filesystems.
    """
    stem = source.name[:-len(source.suffix)] if source.suffix.lower() in _SIDECAR_SUFFIXES else source.name
    for candidate in (f"{stem}.{extension.lower()}", f"{stem}.{extension.upper()}"):
        sibling = source.with_name(candidate)
        if sibling.is_file():
            return sibling

    wanted = f"{stem}.{extension}".lower()
    try:
        entries = sorted(os.listdir(source.parent))
    except OSError:
        return None
    for name in entries:
        if name.lower() == wanted:
            sibling = source.with_name(name)
            if sibling.is_file():
                return sibling
    return None


def _read_table_header(dbf_path: Path) -> bytes:
    """Return the dBASE header: the 32-byte prefix plus the descriptor array."""
    with open(dbf_path, "rb") as handle:
        prefix = handle.read(_TABLE_HEADER_SIZE)
        if len(prefix) < _TABLE_HEADER_SIZE:
            raise ValueError(f"{dbf_path}: too short to be a dBASE table")
        header_size = int.from_bytes(prefix[_HEADER_SIZE_RANGE], "little")
        if header_size < _TABLE_HEADER_SIZE + 1:
            raise ValueError(f"{dbf_path}: implausible dBASE header size {header_size}")
        return prefix + handle.read(header_size - _TABLE_HEADER_SIZE)


def _candidate_encodings(dbf_path: Path, ldid: int) -> list[str]:
    """Encodings to try for field names, most authoritative first."""
    ordered = [_cpg_encoding(dbf_path), _LDID_ENCODINGS.get(ldid), "utf-8"]
    return list(dict.fromkeys(name for name in ordered if name))


def _cpg_encoding(dbf_path: Path) -> str | None:
    """Read the declared encoding from the ``.cpg`` sidecar, if there is one."""
    cpg_path = _sidecar(dbf_path, "cpg")
    if cpg_path is None:
        return None
    try:
        declared = cpg_path.read_bytes().decode("ascii", "ignore")
    except OSError:
        return None

    token = _CPG_TOKEN.search(declared)
    if token is None:
        return None
    label = token.group(0)

    tagged = _LDID_TAG.match(label)
    if tagged is not None:
        return _LDID_ENCODINGS.get(int(tagged.group(1)))
    if label.isdigit():
        return _codec_name(_CODE_PAGE_ALIASES.get(int(label), f"cp{label}"))
    return _codec_name(label)


def _codec_name(label: str) -> str | None:
    try:
        return codecs.lookup(label).name
    except LookupError:
        return None


def _decode(raw: bytes, encodings: list[str]) -> str:
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")  # single-byte: always succeeds