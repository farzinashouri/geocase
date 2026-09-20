from pathlib import Path

def shapefile_attrs(path):
    dbf_path = Path(path).with_suffix('.dbf')
    field_names = []
    
    with open(dbf_path, 'rb') as f:
        f.seek(32)
        
        while True:
            field_desc = f.read(32)
            
            if not field_desc or field_desc[0:1] == b'\x0d':
                break
            
            field_name = field_desc[0:11].rstrip(b'\x00').decode('ascii')
            
            if field_name:
                field_names.append(field_name)
    
    return field_names