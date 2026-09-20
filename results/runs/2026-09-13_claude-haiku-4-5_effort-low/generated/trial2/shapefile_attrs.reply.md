```python
import struct
from pathlib import Path


def shapefile_attrs(path):
    """
    Read attribute field names from an ESRI Shapefile.
    
    Args:
        path: Path to the .shp file (sidecar .dbf file is read)
        
    Returns:
        List of attribute field names in the order they appear in the file
    """
    dbf_path = Path(path).with_suffix('.dbf')
    
    field_names = []
    
    with open(dbf_path, 'rb') as f:
        # Skip the 32-byte DBF header
        f.read(32)
        
        # Read field descriptors (32 bytes each)
        while True:
            field_desc = f.read(32)
            if not field_desc or field_desc[0:1] == b'\x0d':
                break
            # Field name is the first 11 bytes, null-terminated ASCII
            name = field_desc[:11].split(b'\x00')[0].decode('ascii')
            field_names.append(name)
    
    return field_names
```