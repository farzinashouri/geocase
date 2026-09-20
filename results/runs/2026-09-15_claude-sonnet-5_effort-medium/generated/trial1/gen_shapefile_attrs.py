import struct


def shapefile_attrs(path):
    dbf_path = path[:-4] + ".dbf" if path.lower().endswith(".shp") else path

    with open(dbf_path, "rb") as f:
        header = f.read(32)
        header_size = struct.unpack("<H", header[8:10])[0]

        field_names = []
        remaining = f.read(header_size - 32)
        offset = 0
        while offset < len(remaining):
            if remaining[offset] == 0x0D:
                break
            field_descriptor = remaining[offset:offset + 32]
            raw_name = field_descriptor[:11]
            name = raw_name.split(b"\x00", 1)[0].decode("latin-1")
            field_names.append(name)
            offset += 32

    return field_names