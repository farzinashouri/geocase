import pathlib
import struct
from typing import List


def shapefile_attrs(path: str | pathlib.Path) -> List[str]:
    """
    Return the attribute field names of an ESRI Shapefile.

    The function reads the associated .dbf file (same base name as the .shp)
    and extracts the field names from its header in the order they appear.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the .shp file (or any sidecar file; the .dbf is inferred).

    Returns
    -------
    list[str]
        List of field names exactly as stored in the .dbf file.

    Raises
    ------
    FileNotFoundError
        If the corresponding .dbf file does not exist.
    ValueError
        If the .dbf file is malformed or cannot be parsed.
    """
    shp_path = pathlib.Path(path)
    dbf_path = shp_path.with_suffix(".dbf")

    if not dbf_path.is_file():
        raise FileNotFoundError(f"DBF file not found: {dbf_path}")

    with dbf_path.open("rb") as f:
        # Read the first 32 bytes of the DBF header
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("DBF file too small to contain a valid header")

        # The header length is stored in bytes 8-9 (little-endian unsigned short)
        header_length = struct.unpack("<H", header[8:10])[0]
        if header_length < 32:
            raise ValueError("Invalid DBF header length")

        # We have already read 32 bytes; the rest of the header (field descriptors)
        # follows. We'll read field descriptors one by one (32 bytes each) until
        # we encounter the field terminator (0x0D) or exhaust the header.
        fields = []
        # The first field descriptor starts at byte 32 of the file.
        # We'll read from the current file position (which is at 32).
        while True:
            field_desc = f.read(32)
            if len(field_desc) < 32:
                # End of header reached unexpectedly
                break
            # Field terminator is a single byte 0x0D at the start of a descriptor
            if field_desc[0] == 0x0D:
                break

            # Field name: first 11 bytes, null-padded
            name_bytes = field_desc[:11]
            # Strip trailing nulls
            name_bytes = name_bytes.split(b"\x00", 1)[0]
            # Decode using latin-1 to preserve any byte values (DBF typically uses ASCII/Latin-1)
            try:
                name = name_bytes.decode("latin-1")
            except UnicodeDecodeError:
                # Fallback: replace undecodable bytes
                name = name_bytes.decode("ascii", errors="replace")
            fields.append(name)

        # Sanity check: we should have consumed exactly header_length - 32 bytes
        # of field descriptors plus the terminator byte. Not strictly required.

    return fields