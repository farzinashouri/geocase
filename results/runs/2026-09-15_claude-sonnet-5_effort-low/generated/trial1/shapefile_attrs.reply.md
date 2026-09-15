```python
import struct


def shapefile_attrs(path: str) -> list[str]:
    dbf_path = path[:-4] + ".dbf" if path.lower().endswith(".shp") else path

    with open(dbf_path, "rb") as f:
        header = f.read(32)
        num_fields = (struct.unpack("<H", header[8:10])[0] - 33) // 32

        fields = []
        for _ in range(num_fields):
            field_desc = f.read(32)
            name = field_desc[:11].split(b"\x00", 1)[0].decode("ascii")
            fields.append(name)

    return fields
```