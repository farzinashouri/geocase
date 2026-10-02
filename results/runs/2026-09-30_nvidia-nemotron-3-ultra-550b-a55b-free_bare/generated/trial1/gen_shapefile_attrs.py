import os
import struct

def shapefile_attrs(path: str) -> list[str]:
    """
    Return the attribute field names of an ESRI Shapefile as a list of strings,
    in the order they appear in the associated .dbf file.

    Parameters
    ----------
    path : str
        Path to the .shp file (the .dbf sidecar must exist alongside it).

    Returns
    -------
    list[str]
        Field names exactly as stored in the .dbf header (null/space trimmed).

    Raises
    ------
    FileNotFoundError
        If the corresponding .dbf file does not exist.
    ValueError
        If the .dbf file is malformed or too small.
    """
    base, _ = os.path.splitext(path)
    dbf_path = base + ".dbf"

    if not os.path.isfile(dbf_path):
        raise FileNotFoundError(f"DBF sidecar not found: {dbf_path}")

    with open(dbf_path, "rb") as f:
        # Read the 32-byte file header
        header = f.read(32)
        if len(header) < 32:
            raise ValueError("DBF file is too small to contain a valid header")

        # Header layout (little-endian):
        #   0: version byte
        #   1-3: last update (YY, MM, DD)
        #   4-7: number of records (uint32)
        #   8-9: header length in bytes (uint16) — includes terminator
        #   10-11: record length in bytes (uint16)
        #   12-31: reserved
        num_records = struct.unpack("<I", header[4:8])[0]
        header_length = struct.unpack("<H", header[8:10])[0]
        record_length = struct.unpack("<H", header[10:12])[0]

        # Field descriptors start at byte 32, each 32 bytes long.
        # The header ends with a single 0x0D (carriage return) terminator byte.
        f.seek(32)
        field_names = []

        while True:
            # Peek at the first byte of the next field descriptor
            first_byte = f.read(1)
            if not first_byte:
                break  # EOF (should not happen before terminator)
            if first_byte == b"\r":  # 0x0D terminator
                break

            # Read the remaining 31 bytes of the 32-byte descriptor
            rest = f.read(31)
            if len(rest) < 31:
                raise ValueError("Truncated field descriptor in DBF header")

            descriptor = first_byte + rest

            # Field name: first 11 bytes, null-terminated, ASCII
            name_bytes = descriptor[:11]
            # Decode as ASCII, strip trailing nulls and spaces
            name = name_bytes.decode("ascii", errors="ignore").rstrip("\x00").rstrip()
            field_names.append(name)

        return field_names