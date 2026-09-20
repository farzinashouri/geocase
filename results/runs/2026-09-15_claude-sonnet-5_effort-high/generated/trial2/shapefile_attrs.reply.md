```python
"""Read attribute field names from an ESRI Shapefile's .dbf sidecar file."""

import struct
from pathlib import Path


def _find_dbf(shp_path: Path) -> Path:
    dbf_path = shp_path.with_suffix(".dbf")
    if dbf_path.exists():
        return dbf_path

    stem_lower = shp_path.stem.lower()
    for candidate in shp_path.parent.iterdir():
        if candidate.suffix.lower() == ".dbf" and candidate.stem.lower() == stem_lower:
            return candidate

    return dbf_path


def shapefile_attrs(path) -> list[str]:
    shp_path = Path(path)
    dbf_path = _find_dbf(shp_path)

    field_names: list[str] = []
    with open(dbf_path, "rb") as f:
        f.seek(32)
        while True:
            descriptor = f.read(32)
            if len(descriptor) < 32 or descriptor[0] == 0x0D:
                break
            raw_name = descriptor[:11].split(b"\x00", 1)[0]
            field_names.append(raw_name.decode("latin-1"))

    return field_names
```