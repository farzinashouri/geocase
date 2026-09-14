```python
def shapefile_attrs(path):
    """
    Read attribute field names from an ESRI Shapefile DBF file.
    
    Args:
        path: Path to the shapefile (.shp file or base path)
    
    Returns:
        List of field names in the order they appear in the DBF file
    """
    path_str = str(path)
    if path_str.endswith('.shp'):
        dbf_path = path_str[:-4] + '.dbf'
    elif path_str.endswith('.dbf'):
        dbf_path = path_str
    else:
        dbf_path = path_str + '.dbf'
    
    field_names = []
    
    with open(dbf_path, 'rb') as f:
        f.seek(32)
        
        while True:
            field_desc = f.read(32)
            
            if not field_desc or field_desc[0] == 0x0d:
                break
            
            field_name = field_desc[:11].rstrip(b'\x00').decode('ascii')
            field_names.append(field_name)
    
    return field_names
```