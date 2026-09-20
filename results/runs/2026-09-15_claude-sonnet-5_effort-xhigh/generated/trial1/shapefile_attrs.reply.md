```python
"""Read attribute field names from an ESRI Shapefile's .dbf sidecar file."""

from pathlib import Path


def shapefile_attrs(path):
    """Return the attribute field names of an ESRI Shapefile, in file order.

    ``path`` points to the .shp file; the field names are stored in the
    accompanying .dbf file, which must sit alongside it.
    """
    shp_path = Path(path)
    dbf_path = _find_sidecar(shp_path, ".dbf")

    field_names = []
    with open(dbf_path, "rb") as f:
        header = f.read(32)
        if len(header) < 32:
            raise ValueError(f"Invalid DBF file: {dbf_path}")

        while True:
            descriptor = f.read(32)
            if len(descriptor) < 32 or descriptor[0] == 0x0D:
                break
            raw_name = descriptor[0:11].split(b"\x00", 1)[0]
            field_names.append(raw_name.decode("latin-1"))

    return field_names


def _find_sidecar(shp_path, suffix):
    candidates = [
        shp_path.with_suffix(suffix),
        shp_path.with_suffix(suffix.upper()),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No {suffix} sidecar file found for shapefile: {shp_path}"
    )
```