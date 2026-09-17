"""Read attribute field names from an ESRI Shapefile's DBF sidecar."""

import os
import struct


def shapefile_attrs(path):
    """Return the attribute field names of the shapefile at ``path``, in file order."""
    base, _ = os.path.splitext(path)
    dbf_path = None
    for candidate in (base + ".dbf", base + ".DBF"):
        if os.path.isfile(candidate):
            dbf_path = candidate
            break
    if dbf_path is None:
        raise FileNotFoundError(f"No .dbf sidecar found for {path!r}")

    with open(dbf_path, "rb") as fh:
        header = fh.read(32)
        if len(header) < 32:
            raise ValueError(f"{dbf_path!r}: truncated DBF header")
        header_len = struct.unpack("<H", header[8:10])[0]
        num_fields = max(0, (header_len - 33) // 32)
        names = []
        for _ in range(num_fields):
            desc = fh.read(32)
            if len(desc) < 32 or desc[0] == 0x0D:
                break
            raw = desc[:11].split(b"\x00", 1)[0]
            try:
                name = raw.decode("ascii")
            except UnicodeDecodeError:
                name = raw.decode("latin-1")
            names.append(name)
    return names