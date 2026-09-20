import struct


def shapefile_attrs(path):
    dbf_path = path[:-4] + ".dbf" if path.lower().endswith(".shp") else path

    with open(dbf_path, "rb") as f:
        header = f.read(32)
        header_size = struct.unpack("<H", header[8:10])[0]
        f.seek(32)
        fields = []
        while f.tell() < header_size - 1:
            field_desc = f.read(32)
            if field_desc[0:1] == b"\x0d":
                break
            name = field_desc[0:11].split(b"\x00")[0].decode("latin-1")
            fields.append(name)

    return fields