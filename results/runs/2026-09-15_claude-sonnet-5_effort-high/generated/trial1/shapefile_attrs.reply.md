No sidecar-reading library is in the allowed set (fiona/pyshp aren't listed), so this parses the `.dbf` header directly with `struct` from the standard library.

```python
"""Read attribute field names from an ESRI Shapefile's .dbf sidecar."""

import struct
from pathlib import Path


def _find_dbf_path(shp_path: Path) -> Path:
    for suffix in (".dbf", ".DBF"):
        candidate = shp_path.with_suffix(suffix)
        if candidate.exists():
            return candidate

    stem_lower = shp_path.stem.lower()
    for entry in shp_path.parent.iterdir():
        if entry.suffix.lower() == ".dbf" and entry.stem.lower() == stem_lower:
            return entry

    raise FileNotFoundError(f"No .dbf sidecar file found for {shp_path}")


def shapefile_attrs(path) -> list[str]:
    """Return the attribute field names of a shapefile, in file order."""
    shp_path = Path(path)
    dbf_path = _find_dbf_path(shp_path)

    with open(dbf_path, "rb") as f:
        preamble = f.read(32)
        header_size = struct.unpack("<H", preamble[8:10])[0]
        f.seek(32)
        descriptors = f.read(header_size - 32)

    field_names = []
    for offset in range(0, len(descriptors), 32):
        descriptor = descriptors[offset:offset + 32]
        if len(descriptor) < 32 or descriptor[0] == 0x0D:
            break
        raw_name = descriptor[0:11].split(b"\x00", 1)[0]
        field_names.append(raw_name.decode("latin-1"))

    return field_names
```