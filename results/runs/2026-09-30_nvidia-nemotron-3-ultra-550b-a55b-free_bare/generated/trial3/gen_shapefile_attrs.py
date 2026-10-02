import os
import struct

def shapefile_attrs(path):
    """Return the attribute field names of an ESRI Shapefile as a list of strings.

    Args:
        path: Path to the .shp file (sidecar .dbf must be present).

    Returns:
        List of field names in the order they appear in the .dbf file.
    """
    base, _ = os.path.splitext(path)
    dbf_path = base + '.dbf'

    with open(dbf_path, 'rb') as f:
        # Read the main header (32 bytes)
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("DBF file too small to contain a valid header")

        # Unpack header fields (little-endian)
        # Version (1 byte), year (1 byte), month (1 byte), day (1 byte),
        # number of records (4 bytes), header length (2 bytes), record length (2 bytes)
        version, year, month, day, num_records, header_len, record_len = struct.unpack(
            '<BBBBLHH', header[:16]
        )

        # The header length includes the 32-byte header, field descriptors (32 bytes each),
        # and a single 0x0D terminator byte.
        # We'll read field descriptors until we encounter the terminator.
        field_names = []
        while True:
            field_desc = f.read(32)
            if not field_desc:
                break
            # Terminator byte (0x0D) marks end of field descriptors
            if field_desc[0] == 0x0D:
                break

            # Field name: first 11 bytes, null-padded
            name_bytes = field_desc[:11]
            # Find the first null byte
            null_idx = name_bytes.find(b'\x00')
            if null_idx >= 0:
                name = name_bytes[:null_idx].decode('ascii', errors='replace')
            else:
                name = name_bytes.decode('ascii', errors='replace')
            field_names.append(name)

        return field_names