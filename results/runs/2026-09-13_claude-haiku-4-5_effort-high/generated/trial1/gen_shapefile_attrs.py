def shapefile_attrs(path):
    from pathlib import Path
    
    # Get DBF file path (shapefile attributes are stored in .dbf)
    base_path = Path(path).with_suffix('')
    dbf_path = base_path.with_suffix('.dbf')
    
    field_names = []
    
    with open(dbf_path, 'rb') as f:
        # Skip 32-byte DBF header
        f.seek(32)
        
        # Read field descriptors until terminator
        while True:
            field_desc = f.read(32)
            
            # Field descriptors are terminated by a 0x0D byte
            if not field_desc or field_desc[0] == 0x0d:
                break
            
            # Extract field name from first 11 bytes (null-padded ASCII string)
            field_name = field_desc[:11].rstrip(b'\x00').decode('ascii')
            field_names.append(field_name)
    
    return field_names