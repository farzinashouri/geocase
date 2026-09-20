"""Read attribute field names from an ESRI Shapefile (.dbf header)."""

import struct


def shapefile_attrs(path):
    dbf_path = _sibling_path(path, ".dbf")
    with open(dbf_path, "rb") as f:
        header = f.read(32)
        num_fields = (struct.unpack("<H", header[8:10])[0] - 33) // 32

        names = []
        for _ in range(num_fields):
            field_desc = f.read(32)
            raw_name = field_desc[0:11]
            name = raw_name.split(b"\x00", 1)[0].decode("ascii")
            names.append(name)

        return names


def _sibling_path(path, new_ext):
    if path.lower().endswith(".shp"):
        base = path[: -len(".shp")]
    else:
        base = path
    return base + new_ext