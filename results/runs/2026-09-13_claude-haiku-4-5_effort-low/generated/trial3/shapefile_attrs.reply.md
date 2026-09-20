```python
def shapefile_attrs(path):
    """Read attribute field names from an ESRI Shapefile."""
    if path.endswith('.shp'):
        base_path = path[:-4]
    else:
        base_path = path
    
    dbf_path = base_path + '.dbf'
    
    with open(dbf_path, 'rb') as f:
        # Skip dBASE header (32 bytes)
        f.read(32)
        
        fields = []
        while True:
            # Read 32-byte field descriptor
            field_descriptor = f.read(32)
            
            # End of field descriptors marked by 0x0D
            if not field_descriptor or field_descriptor[0] == 0x0D:
                break
            
            # Field name is first 11 bytes, null-terminated
            field_name = field_descriptor[0:11].rstrip(b'\x00').decode('latin-1')
            fields.append(field_name)
    
    return fields
```