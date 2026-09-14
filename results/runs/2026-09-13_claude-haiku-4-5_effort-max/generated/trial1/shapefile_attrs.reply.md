```python
from pathlib import Path

def shapefile_attrs(path):
    """Read attribute field names from an ESRI Shapefile."""
    dbf_path = Path(path).with_suffix('.dbf')
    
    if not dbf_path.exists():
        raise FileNotFoundError(f"DBF file not found: {dbf_path}")
    
    fields = []
    
    with open(dbf_path, 'rb') as f:
        f.seek(32)
        
        while True:
            field_data = f.read(32)
            
            if not field_data or field_data[0:1] == b'\x0d':
                break
            
            field_name = field_data[0:11].rstrip(b'\x00').decode('latin1')
            
            if field_name:
                fields.append(field_name)
    
    return fields
```