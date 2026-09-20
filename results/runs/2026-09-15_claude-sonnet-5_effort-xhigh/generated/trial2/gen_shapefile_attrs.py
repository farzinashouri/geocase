"""Read attribute field names from an ESRI Shapefile's companion .dbf file."""

import struct
from pathlib import Path

_DBF_HEADER_SIZE = 32
_FIELD_DESCRIPTOR_SIZE = 32
_FIELD_TERMINATOR = 0x0D


def shapefile_attrs(path):
    """Return the attribute field names of a shapefile, in file order.

    Field names live in the .shp file's companion .dbf sidecar, not in the
    .shp file itself, so this reads that sidecar's header directly.
    """
    dbf_path = Path(path).with_suffix(".dbf")

    with open(dbf_path, "rb") as f:
        header = f.read(_DBF_HEADER_SIZE)
        if len(header) < _DBF_HEADER_SIZE:
            raise ValueError(f"Invalid DBF header in {dbf_path}")

        header_size = struct.unpack("<H", header[8:10])[0]
        descriptors = f.read(header_size - _DBF_HEADER_SIZE)

    names = []
    offset = 0
    while offset < len(descriptors):
        if descriptors[offset] == _FIELD_TERMINATOR:
            break

        descriptor = descriptors[offset:offset + _FIELD_DESCRIPTOR_SIZE]
        if len(descriptor) < _FIELD_DESCRIPTOR_SIZE:
            break

        raw_name = descriptor[0:11]
        name = raw_name.split(b"\x00", 1)[0].decode("latin-1")
        names.append(name)

        offset += _FIELD_DESCRIPTOR_SIZE

    return names