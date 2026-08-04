"""Format compliance assertions — verify files match their declared format.

Each validator performs the cheapest reliable "is this file really this
format?" check: magic-byte inspection, structural parse, or schema read.
No validator loads a full GeoDataFrame — that is the job of the loader tests.

All public functions raise :class:`AssertionError` on failure so they
plug into pytest naturally.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import struct
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

# ===================================================================
# Public entry points
# ===================================================================


def assert_format_compliance(path: Path, declared_format: str) -> None:
    """Validate that *path* truly matches *declared_format*.

    Dispatches to a format-specific validator.  Raises
    :class:`AssertionError` with a clear message on mismatch.

    Args:
        path: Absolute path to the primary data file.
        declared_format: The ``format`` value from ``case.yaml``
            (e.g. ``"GeoJSON"``, ``"Parquet"``, ``"GPKG"``).
    """
    validator = _VALIDATORS.get(declared_format)
    if validator is None:
        raise AssertionError(
            f"No format validator registered for '{declared_format}'. "
            f"Known formats: {sorted(_VALIDATORS)}"
        )
    validator(path)


def registered_format_validators() -> frozenset[str]:
    """Return the set of format names that have a registered validator.

    Useful for testing that the dispatch table stays in sync with
    :data:`~geocase.catalog.models.FormatType`.
    """
    return frozenset(_VALIDATORS)


def assert_geoparquet_metadata(path: Path) -> None:
    """Verify the Parquet file contains valid GeoParquet metadata.

    Checks that the ``geo`` metadata key exists in the Parquet schema
    metadata, is valid JSON, and contains ``primary_column`` and
    ``columns`` per the GeoParquet 1.0/1.1 spec.

    Raises:
        AssertionError: On any structural problem.
    """
    import pyarrow.parquet as pq

    schema = pq.read_schema(str(path))

    assert schema.metadata is not None, (
        f"Parquet file has no schema metadata at all: {path.name}"
    )
    assert b"geo" in schema.metadata, (
        f"Parquet file lacks 'geo' metadata key (not GeoParquet): {path.name}"
    )

    raw = schema.metadata[b"geo"]
    try:
        geo = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AssertionError(
            f"'geo' metadata is not valid JSON in {path.name}: {exc}"
        ) from exc

    assert isinstance(geo, dict), f"'geo' metadata is not a JSON object in {path.name}"
    assert "primary_column" in geo, (
        f"GeoParquet metadata missing 'primary_column' in {path.name}"
    )
    assert "columns" in geo, f"GeoParquet metadata missing 'columns' in {path.name}"


# ===================================================================
# Per-format validators (private)
# ===================================================================

_GEOJSON_TYPES = frozenset(
    {
        "Feature",
        "FeatureCollection",
        "GeometryCollection",
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }
)

_WKT_COLUMN_NAMES = frozenset({"wkt", "geometry_wkt", "geometry"})


def _validate_geojson(path: Path) -> None:
    """GeoJSON: must parse as JSON with a recognized GeoJSON ``type``."""
    try:
        with path.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AssertionError(f"File is not valid JSON: {path.name} — {exc}") from exc

    if not isinstance(data, dict):
        raise AssertionError(
            f"GeoJSON root must be an object, got {type(data).__name__}: {path.name}"
        )

    top_type = data.get("type")
    if top_type not in _GEOJSON_TYPES:
        raise AssertionError(
            f"GeoJSON 'type' is '{top_type}', expected one of "
            f"{sorted(_GEOJSON_TYPES)}: {path.name}"
        )


def _validate_parquet(path: Path) -> None:
    """Parquet: first 4 bytes must be ``PAR1``."""
    with path.open("rb") as f:
        magic = f.read(4)
    if magic != b"PAR1":
        raise AssertionError(
            f"File does not start with Parquet magic bytes PAR1: "
            f"{path.name} (got {magic!r})"
        )


def _validate_gpkg(path: Path) -> None:
    """GeoPackage: SQLite header + ``gpkg_contents`` table must exist."""
    _assert_sqlite_header(path)
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gpkg_contents'"
        )
        if cur.fetchone() is None:
            raise AssertionError(
                f"File is SQLite but has no 'gpkg_contents' table "
                f"(not a valid GeoPackage): {path.name}"
            )
    finally:
        conn.close()


def _validate_shapefile(path: Path) -> None:
    """Shapefile: magic int 9994 (big-endian) + ``.shx``/``.dbf`` sidecars."""
    with path.open("rb") as f:
        raw = f.read(4)
    if len(raw) < 4:
        raise AssertionError(f"Shapefile too small to contain magic bytes: {path.name}")
    magic = struct.unpack(">i", raw)[0]
    if magic != 9994:
        raise AssertionError(
            f"Shapefile magic int is {magic}, expected 9994: {path.name}"
        )

    stem = path.stem
    parent = path.parent
    for ext in (".shx", ".dbf"):
        sidecar = parent / f"{stem}{ext}"
        if not sidecar.is_file():
            raise AssertionError(
                f"Shapefile sidecar missing: {sidecar.name} "
                f"(required alongside {path.name})"
            )


def _validate_kml(path: Path) -> None:
    """KML: must parse as XML with a root tag containing ``kml``."""
    try:
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError as exc:
        raise AssertionError(f"File is not valid XML: {path.name} — {exc}") from exc

    root = tree.getroot()
    # Namespace-aware: {http://www.opengis.net/kml/2.2}kml
    tag = root.tag.lower()
    if "kml" not in tag:
        raise AssertionError(
            f"XML root tag is '{root.tag}', expected a KML root element: {path.name}"
        )


def _validate_gml(path: Path) -> None:
    """GML: must parse as XML with a GML/OGR namespace or FeatureCollection tag."""
    try:
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError as exc:
        raise AssertionError(f"File is not valid XML: {path.name} — {exc}") from exc

    root = tree.getroot()
    tag_lower = root.tag.lower()
    # OGR-produced GML often has ogr:FeatureCollection with gml namespace attrs
    # Official GML uses http://www.opengis.net/gml or gml/3.2
    is_gml = (
        "gml" in tag_lower
        or "featurecollection" in tag_lower
        or "http://www.opengis.net/gml" in tag_lower
    )
    if not is_gml:
        raise AssertionError(
            f"XML root tag '{root.tag}' does not look like GML: {path.name}"
        )


def _validate_sqlite(path: Path) -> None:
    """SQLite (non-GPKG): SQLite header present, ``gpkg_contents`` absent."""
    _assert_sqlite_header(path)
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gpkg_contents'"
        )
        if cur.fetchone() is not None:
            raise AssertionError(
                f"File declared as SQLite but has 'gpkg_contents' table "
                f"(looks like a GeoPackage instead): {path.name}"
            )
    finally:
        conn.close()


def _validate_flatgeobuf(path: Path) -> None:
    """FlatGeobuf: first 4 bytes are ``fgb\\x03`` (magic + version byte)."""
    with path.open("rb") as f:
        magic = f.read(4)
    # FlatGeobuf magic: 0x66 0x67 0x62 0x03  →  b"fgb\x03"
    if magic[:3] != b"fgb":
        raise AssertionError(
            f"File does not start with FlatGeobuf magic bytes: "
            f"{path.name} (got {magic!r})"
        )


def _validate_arrow_ipc(path: Path) -> None:
    """Arrow / Feather / GeoArrow: IPC file starts with ``ARROW1``."""
    with path.open("rb") as f:
        magic = f.read(6)
    if magic != b"ARROW1":
        raise AssertionError(
            f"File does not start with Arrow IPC magic 'ARROW1': "
            f"{path.name} (got {magic!r})"
        )


def _validate_csv_wkt(path: Path) -> None:
    """CSV_WKT: parseable CSV with a WKT-like column in the header."""
    try:
        with path.open(newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise AssertionError(
            f"File is not a parseable CSV: {path.name} — {exc}"
        ) from exc

    if header is None:
        raise AssertionError(f"CSV file is empty: {path.name}")

    lower_header = {col.strip().lower() for col in header}
    if not lower_header & _WKT_COLUMN_NAMES:
        raise AssertionError(
            f"CSV has no WKT column (expected one of {sorted(_WKT_COLUMN_NAMES)}). "
            f"Header: {header} — {path.name}"
        )


def _validate_wkt(path: Path) -> None:
    """WKT: text file parseable by shapely.wkt.loads."""
    from shapely import wkt

    text = path.read_text().strip()
    if not text:
        raise AssertionError(f"WKT file is empty: {path.name}")
    try:
        wkt.loads(text)
    except Exception as exc:
        raise AssertionError(
            f"File content is not valid WKT: {path.name} — {exc}"
        ) from exc


def _validate_wkb(path: Path) -> None:
    """WKB: binary (or hex-encoded) content parseable by shapely.wkb.loads."""
    from shapely import wkb

    raw = path.read_bytes()
    if not raw:
        raise AssertionError(f"WKB file is empty: {path.name}")
    try:
        wkb.loads(raw)
    except Exception:
        # Might be hex-encoded
        try:
            wkb.loads(bytes.fromhex(raw.decode("ascii").strip()))
        except Exception as exc:
            raise AssertionError(
                f"File content is not valid WKB (binary or hex): {path.name} — {exc}"
            ) from exc


# ===================================================================
# Helpers
# ===================================================================


def _assert_sqlite_header(path: Path) -> None:
    """Assert the first 16 bytes are the SQLite file header."""
    with path.open("rb") as f:
        header = f.read(16)
    if header != b"SQLite format 3\x00":
        raise AssertionError(
            f"File does not start with SQLite header: {path.name} (got {header!r})"
        )


# ===================================================================
# Validator dispatch table
# ===================================================================

_VALIDATORS: dict[str, Callable[[Path], None]] = {
    "GeoJSON": _validate_geojson,
    "Parquet": _validate_parquet,
    "GPKG": _validate_gpkg,
    "Shapefile": _validate_shapefile,
    "KML": _validate_kml,
    "GML": _validate_gml,
    "SQLite": _validate_sqlite,
    "FlatGeobuf": _validate_flatgeobuf,
    "Feather": _validate_arrow_ipc,
    "Arrow": _validate_arrow_ipc,
    "GeoArrow": _validate_arrow_ipc,
    "CSV_WKT": _validate_csv_wkt,
    "WKT": _validate_wkt,
    "WKB": _validate_wkb,
}
