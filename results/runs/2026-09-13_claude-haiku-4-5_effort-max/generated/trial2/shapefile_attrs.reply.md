```python
import struct
from pathlib import Path

def shapefile_attrs(path):
    """Return attribute field names from a shapefile's .dbf file."""
    dbf_path = Path(path).with_suffix('.dbf')
    
    with open(dbf_path, 'rb') as f:
        # Read header (32 bytes)
        header = f.read(32)
        
        # Header length is at bytes 8-9 (little-endian)
        header_length = struct.unpack('<H', header[8:10])[0]
        
        # Field descriptors start at byte 32
        field_names = []
        f.seek(32)
        
        while f.tell() < header_length:
            field_descriptor = f.read(32)
            
            # Make sure we read 32 bytes
            if len(field_descriptor) < 32:
                break
            
            # Check for field descriptor terminator (0x0D)
            if field_descriptor[0] == 0x0D:
                break
            
            # Field name is bytes 0-10 (11 bytes total)
            field_name_bytes = field_descriptor[:11]
            # Decode as ASCII and remove null terminator if present
            field_name = field_name_bytes.decode('ascii').split('\x00')[0]
            field_names.append(field_name)
    
    return field_names
```