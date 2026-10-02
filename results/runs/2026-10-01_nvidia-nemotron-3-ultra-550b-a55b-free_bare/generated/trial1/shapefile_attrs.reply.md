```python
import os
import struct

def shapefile_attrs(path):
    """
    Return the attribute field names of an ESRI Shapefile.

    Parameters
    ----------
    path : str
        Path to the .shp file (or .dbf file). The corresponding .dbf file
        (same base name, .dbf extension) is read to extract field names.

    Returns
    -------
    list[str]
        Field names in the order they appear in the dBase table.

    Raises
    ------
    FileNotFoundError
        If the .dbf file does not exist.
    ValueError
        If the .dbf file is malformed.
    """
    # Determine the .dbf path
    base, ext = os.path.splitext(path)
    if ext.lower() == '.dbf':
        dbf_path = path
    else:
        dbf_path = base + '.dbf'

    if not os.path.exists(dbf_path):
        raise FileNotFoundError(f"DBF file not found: {dbf_path}")

    with open(dbf_path, 'rb') as f:
        # Read the fixed 32-byte header
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("DBF file too short to contain a valid header")

        # Header length is stored as a little-endian unsigned short at offset 8
        header_length = struct.unpack_from('<H', header, 8)[0]

        # The header includes the first 32 bytes, field descriptors (32 bytes each),
        # and a single terminator byte (0x0D). Read the remainder of the header.
        remaining = header_length - 32
        if remaining < 1:
            return []  # No fields

        rest = f.read(remaining)
        if len(rest) < remaining:
            raise ValueError("DBF header truncated")

        field_names = []
        i = 0
        while i < len(rest):
            # Terminator byte
            if rest[i] == 0x0D:
                break
            # Each field descriptor is exactly 32 bytes
            if i + 32 > len(rest):
                break
            desc = rest[i:i+32]
            # Field name: first 11 bytes, null-terminated
            name_bytes = desc[:11]
            null_pos = name_bytes.find(b'\x00')
            if null_pos >= 0:
                name_bytes = name_bytes[:null_pos]
            # Decode using latin-1 to preserve exact byte values
            field_names.append(name_bytes.decode('latin-1'))
            i += 32

        return field_names
```