```python
from pathlib import Path


def shapefile_attrs(path):
    """
    Read attribute field names from an ESRI Shapefile.
    
    Args:
        path: Path to the .shp or .dbf file
        
    Returns:
        List of field names in order as they appear in the file
    """
    shp_path = Path(path)
    
    # Convert to .dbf path if needed
    if shp_path.suffix.lower() == '.shp':
        dbf_path = shp_path.with_suffix('.dbf')
    else:
        dbf_path = shp_path
    
    field_names = []
    
    with open(dbf_path, 'rb') as f:
        # Field descriptors start at byte 32 in the DBF header
        f.seek(32)
        
        # Read field descriptors (32 bytes each) until terminator (0x0D)
        while True:
            # Read field name area (11 bytes)
            name_bytes = f.read(11)
            
            # Check for end of field descriptors
            if not name_bytes or name_bytes[0] == 0x0D:
                break
            
            # Decode field name (null-terminated ASCII string)
            field_name = name_bytes.split(b'\x00')[0].decode('ascii')
            field_names.append(field_name)
            
            # Skip rest of descriptor (field type + reserved = 21 bytes)
            f.read(21)
    
    return field_names
```