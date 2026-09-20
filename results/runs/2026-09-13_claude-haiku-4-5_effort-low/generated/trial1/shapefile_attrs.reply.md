```python
from pathlib import Path

def shapefile_attrs(path):
    """Read attribute field names from an ESRI Shapefile."""
    dbf_path = Path(path).with_suffix('.dbf')
    
    fields = []
    with open(dbf_path, 'rb') as f:
        f.read(32)  # Skip 32-byte dBASE header
        
        while True:
            field_desc = f.read(32)
            if not field_desc or field_desc[0] == 0x0D:
                break
            
            # Field name is null-terminated ASCII in bytes 0-10
            field_name = field_desc[0:11].rstrip(b'\x00').decode('ascii')
            fields.append(field_name)
    
    return fields
```