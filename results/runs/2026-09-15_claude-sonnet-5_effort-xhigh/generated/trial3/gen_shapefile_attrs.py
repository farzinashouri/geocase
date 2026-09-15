"""Read attribute field names from an ESRI Shapefile's sidecar .dbf file."""

import os
import struct


def _find_dbf_path(path):
    base, _ = os.path.splitext(path)
    for ext in (".dbf", ".DBF", ".Dbf"):
        candidate = base + ext
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f"No .dbf sidecar file found for shapefile: {path}")


def shapefile_attrs(path):
    """Return the attribute field names of an ESRI Shapefile, in file order."""
    dbf_path = _find_dbf_path(path)

    with open(dbf_path, "rb") as f:
        header = f.read(32)
        if len(header) < 32:
            raise ValueError(f"Invalid DBF file: {dbf_path}")

        header_size = struct.unpack("<H", header[8:10])[0]
        descriptors = f.read(header_size - 32)

    field_names = []
    offset = 0
    while offset < len(descriptors) and descriptors[offset] != 0x0D:
        name_bytes = descriptors[offset:offset + 11]
        name = name_bytes.split(b"\x00", 1)[0].decode("latin-1")
        field_names.append(name)
        offset += 32

    return field_names