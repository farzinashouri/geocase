```python
import struct


def shapefile_attrs(path):
    """Return the names of attribute fields in an ESRI Shapefile."""
    # Convert to .dbf path
    if path.endswith('.shp'):
        dbf_path = path[:-4] + '.dbf'
    elif not path.endswith('.dbf'):
        dbf_path = path + '.dbf'
    else:
        dbf_path = path
    
    field_names = []
    
    with open(dbf_path, 'rb') as f:
        # Read and parse file header (32 bytes)
        header = f.read(32)
        header_length = struct.unpack('<H', header[8:10])[0]
        
        # Read field descriptors
        f.seek(32)
        while True:
            pos = f.tell()
            if pos >= header_length:
                break
            
            field_desc = f.read(32)
            if len(field_desc) < 32:
                break
            
            # Check for end marker
            if field_desc[0] == 0x0D:
                break
            
            # Extract field name (null-terminated ASCII)
            field_name = field_desc[0:11].decode('ascii').rstrip('\x00')
            field_names.append(field_name)
    
    return field_names
```