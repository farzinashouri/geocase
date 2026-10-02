import os
import struct
from typing import List

def shapefile_attrs(path: str) -> List[str]:
    """
    Return the attribute field names of an ESRI Shapefile in the order they appear.

    The function reads the associated .dbf file (dBase format) which stores the
    attributes. It parses the field descriptors from the DBF header and returns
    the field names exactly as stored (trailing spaces and nulls removed).

    Parameters
    ----------
    path : str
        Path to the .shp file. The corresponding .dbf file must exist alongside it.

    Returns
    -------
    list[str]
        List of field names in the order they appear in the DBF file.

    Raises
    ------
    FileNotFoundError
        If the .dbf file cannot be found.
    ValueError
        If the DBF file is malformed or too short.
    """
    # Derive the .dbf path from the .shp path
    base, _ = os.path.splitext(path)
    dbf_path = base + ".dbf"

    # Try case-insensitive fallback for the .dbf extension
    if not os.path.exists(dbf_path):
        alt_path = base + ".DBF"
        if os.path.exists(alt_path):
            dbf_path = alt_path
        else:
            raise FileNotFoundError(f"DBF file not found for shapefile: {path}")

    field_names = []
    with open(dbf_path, "rb") as f:
        # Read the main header (32 bytes)
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("DBF file too short to contain a valid header")

        # Header length (bytes 8-9, little-endian unsigned short)
        header_length = struct.unpack("<H", header[8:10])[0]

        # Field descriptors start at byte 32, each 32 bytes, terminated by a 0x0D byte
        pos = 32
        while pos < header_length:
            f.seek(pos)
            field_desc = f.read(32)
            if len(field_desc) < 32:
                break
            # Terminator byte (0x0D) marks end of field descriptors
            if field_desc[0] == 0x0D:
                break

            # Field name: first 11 bytes, null-terminated, padded with spaces
            name_bytes = field_desc[:11]
            # Remove everything after the first null byte
            null_pos = name_bytes.find(b"\x00")
            if null_pos >= 0:
                name_bytes = name_bytes[:null_pos]
            # Decode as ASCII (DBF spec uses ASCII) and strip trailing spaces
            name = name_bytes.decode("ascii", errors="replace").rstrip(" ")
            field_names.append(name)

            pos += 32

    return field_names


__all__ = ["shapefile_attrs"]