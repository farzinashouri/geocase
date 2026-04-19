"""Generate a markdown coverage matrix for core vector cases.

Scans ``src/geocase/data/core/vector/**/case.yaml`` through the catalog loader
and emits a matrix covering geometry types, formats, complexity/validity, and
edge-case categories.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "geocase"
VECTOR_ROOT = PACKAGE_ROOT / "data" / "core" / "vector"

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.loader import load_case_metadata  # noqa: E402


GEOMETRY_TARGETS = [
	"Point",
	"MultiPoint",
	"LineString",
	"MultiLineString",
	"Polygon",
	"MultiPolygon",
	"GeometryCollection",
]

FORMAT_TARGETS: list[tuple[str, list[str]]] = [
	("GeoJSON", ["GeoJSON"]),
	("GPKG", ["GPKG"]),
	("Shapefile", ["Shapefile"]),
	("Parquet", ["Parquet"]),
	("GML", ["GML"]),
	("KML", ["KML"]),
	("CSV_WKT", ["CSV_WKT", "CSV-WKT", "CSV_WKB"]),
	("Feather/Arrow variants", ["Feather", "Arrow", "GeoArrow", "Feather/Arrow"]),
	("WKB", ["WKB"]),
	("WKT", ["WKT"]),
	("SQLite", ["SQLite"]),
	("FlatGeobuf", ["FlatGeobuf", "flatgeobuf", "FlatGeoBuf"]),
]

PHASE2_GAP_DEFINITIONS: list[dict[str, object]] = [
	{
		"axis": "Format-specific",
		"gap_id": "parquet_mixed_schema_attributes",
		"planned_cases": ["parquet_mixed_schema_attributes"],
		"status": "missing",
	},
	{
		"axis": "Format-specific",
		"gap_id": "format_limited_kml_case",
		"planned_cases": ["format_limited_kml_case"],
		"status": "missing",
	},
	{
		"axis": "Spatial complement",
		"gap_id": "north_pole_polygon",
		"planned_cases": ["north_pole_polygon"],
		"status": "missing",
	},
	{
		"axis": "Spatial complement",
		"gap_id": "south_pole_polygon",
		"planned_cases": ["south_pole_polygon"],
		"status": "missing",
	},
	{
		"axis": "Spatial complement",
		"gap_id": "equator_polygon",
		"planned_cases": ["equator_polygon"],
		"status": "missing",
	},
	{
		"axis": "CRS refinement",
		"gap_id": "web_mercator_precision_case",
		"planned_cases": ["web_mercator_precision_case"],
		"status": "deferred",
		"resolution": "Existing web_mercator_baseline is sufficient for v1.0.",
	},
	{
		"axis": "Null-vs-empty semantics",
		"gap_id": "null_geometry_row_gpkg",
		"planned_cases": ["empty_geometry_gpkg"],
		"status": "resolved",
		"resolution": "Covered by empty_geometry_gpkg (has both NULL and EMPTY rows).",
	},
	{
		"axis": "Release policy",
		"gap_id": "matrix-completeness-v1",
		"planned_cases": ["geometrycollection_followups", "columnar_format_followups"],
		"status": "deferred",
		"resolution": "Deferred past v1.0. Core formats cover \u22656/7 geom types.",
	},
]


def _load_vector_metadata(vector_root: Path) -> list[object]:
	"""Load all valid case metadata from vector case directories."""
	metadata_entries: list[object] = []
	for case_yaml in sorted(vector_root.rglob("case.yaml")):
		metadata_entries.append(load_case_metadata(case_yaml))
	return metadata_entries


def _case_text(meta: object) -> str:
	"""Return normalized searchable text for a case."""
	tags = " ".join(getattr(meta, "tags", []))
	risks = " ".join(getattr(meta, "risk_types", []))
	description = getattr(meta, "description", "") or ""
	title = getattr(meta, "title", "") or ""
	identifier = getattr(meta, "id", "") or ""
	params_text = " ".join(str(key) for key in getattr(meta, "params", {}).keys())
	return f"{identifier} {title} {description} {tags} {risks} {params_text}".lower()


def _has_any(text: str, terms: list[str]) -> bool:
	return any(term in text for term in terms)


def _expect_valid_geometry(meta: object) -> bool | None:
	"""Safely return assertion hint for geometry validity expectation."""
	assertions = getattr(meta, "assertions", None)
	if assertions is None:
		return None
	return getattr(assertions, "expect_valid_geometry", None)


def _format_status(fmt: str, count: int) -> str:
	"""Return status label for a format row."""
	if count == 0:
		return "❌ missing in core vector"
	if fmt == "GeoJSON":
		return "✅ broad coverage" if count >= 5 else "⚠️ limited"
	if count == 1:
		return "⚠️ limited (single-case level)"
	return "✅ present"


def _present_required(present: bool) -> str:
	return "✅ present" if present else "❌ missing"


def _phase2_status(case_ids: set[str], definition: dict[str, object]) -> str:
	"""Return the current status label for a Phase 2 gap row."""
	planned_cases = cast(list[str], definition["planned_cases"])
	if any(case_id in case_ids for case_id in planned_cases):
		return "✅ covered in live catalog"

	status = definition["status"]
	if status == "missing":
		return "❌ missing"
	if status == "decision-needed":
		return "⚠️ decision needed"
	if status == "deferred":
		return "↩️ deferred past v1.0"
	if status == "resolved":
		return "✅ resolved (no new case needed)"
	return "⚠️ review"


def _build_markdown(entries: list[object]) -> str:
	"""Build markdown table output for the coverage matrix."""
	geometry_present = {
		geom: any(getattr(meta, "geometry_type", None) == geom for meta in entries)
		for geom in GEOMETRY_TARGETS
	}

	format_counts: dict[str, int] = {
		label: sum(1 for meta in entries if getattr(meta, "format", None) in aliases)
		for label, aliases in FORMAT_TARGETS
	}

	case_ids = {getattr(meta, "id", "") for meta in entries}

	texts = [_case_text(meta) for meta in entries]

	simple_present = any(_has_any(text, ["baseline", "simple"]) for text in texts)
	complex_present = any(
		_has_any(text, ["multipart", "hole", "interior_ring", "dense", "mixed", "geometrycollection"])
		for text in texts
	)

	valid_present = any(_expect_valid_geometry(meta) is not False for meta in entries)
	invalid_present = any(_expect_valid_geometry(meta) is False for meta in entries)
	ambiguous_present = any(
		_has_any(text, ["ambiguous", "engine-dependent", "engine_dependent", "depends on engine"])
		for text in texts
	)
	degenerate_present = any(
		_has_any(text, ["degenerate", "collapsed", "zero-area", "zero area", "zero_length", "zero length"])
		for text in texts
	)
	format_limited_present = any(
		_has_any(text, ["format-limited", "format_limited", "driver-specific", "driver_specific", "format constraint"])
		for text in texts
	)

	spatial_terms: dict[str, list[str]] = {
		"North pole": ["north pole", "north_pole", "arctic", "polar_north"],
		"South pole": ["south pole", "south_pole", "antarctic", "polar_south"],
		"Equator": ["equator", "equatorial"],
		"EPSG:3857": ["epsg:3857", "3857", "web mercator"],
	}

	spatial_status: dict[str, str] = {}
	for label, terms in spatial_terms.items():
		spatial_status[label] = _present_required(any(_has_any(text, terms) for text in texts))

	edge_terms: dict[str, list[str]] = {
		"Antimeridian/dateline": ["antimeridian", "dateline"],
		"CRS mismatch/reprojection": ["crs", "reprojection", "utm", "epsg"],
		"Topology defects": ["topology", "self_intersection", "invalid", "repair"],
		"Schema/encoding issues": ["schema", "encoding"],
		"Empty/null geometry behavior": ["empty", "null"],
		"Precision/rounding artifacts": ["precision", "rounding"],
		"Multipart dissolve/overlay behavior": ["multipart", "dissolve", "overlay"],
	}

	edge_status: dict[str, str] = {}
	for label, terms in edge_terms.items():
		hits = sum(1 for text in texts if _has_any(text, terms))
		if hits == 0:
			edge_status[label] = "❌ missing"
		elif label in {"Empty/null geometry behavior", "Precision/rounding artifacts"} and hits <= 1:
			edge_status[label] = "⚠️ partial"
		else:
			edge_status[label] = "✅ present"

	lines: list[str] = []
	lines.append("### Coverage matrix (current vs target)")
	lines.append("")
	lines.append("Use this matrix as the release gate for \"comprehensive\" status.")
	lines.append("")
	lines.append("#### A) Geometry types")
	lines.append("")
	lines.append("| Geometry type | Current coverage (core vector) | Target |")
	lines.append("|---|---:|---:|")
	for geom in GEOMETRY_TARGETS:
		lines.append(f"| {geom} | {_present_required(geometry_present[geom])} | ✅ required |")

	lines.append("")
	lines.append("#### B) Formats")
	lines.append("")
	lines.append("| Format | Current coverage (core vector) | Target |")
	lines.append("|---|---:|---:|")
	for label, _aliases in FORMAT_TARGETS:
		lines.append(f"| {label} | {_format_status(label, format_counts[label])} | ✅ required |")

	lines.append("")
	lines.append("#### C) Complexity and validity")
	lines.append("")
	lines.append("| Dimension | Current coverage (core vector) | Target |")
	lines.append("|---|---:|---:|")
	lines.append(f"| Simple baseline geometries | {_present_required(simple_present)} | ✅ required |")
	lines.append(f"| Complex/multipart geometries | {_present_required(complex_present)} | ✅ required |")
	lines.append(f"| Valid datasets | {_present_required(valid_present)} | ✅ required |")
	lines.append(f"| Invalid/pathological datasets | {_present_required(invalid_present)} | ✅ required |")
	lines.append(f"| Ambiguous / engine-dependent validity | {_present_required(ambiguous_present)} | ✅ required |")
	lines.append(f"| Degenerate but parseable validity | {_present_required(degenerate_present)} | ✅ required |")
	lines.append(f"| Format-limited validity | {_present_required(format_limited_present)} | ✅ required |")

	lines.append("")
	lines.append("#### D) Spatial reference and geographic coverage")
	lines.append("")
	lines.append("| Category | Current coverage (core vector) | Target |")
	lines.append("|---|---:|---:|")
	for label in spatial_terms:
		lines.append(f"| {label} | {spatial_status[label]} | ✅ required |")

	lines.append("")
	lines.append("#### E) Edge-case categories")
	lines.append("")
	lines.append("| Category | Current coverage (core vector) | Target |")
	lines.append("|---|---:|---:|")
	for label in edge_terms:
		lines.append(f"| {label} | {edge_status[label]} | ✅ required |")

	lines.append("")
	lines.append("#### F) Minimum target policy per matrix cell")
	lines.append("")
	lines.append("- For each supported geometry type × format combination: at least one valid baseline fixture.")
	lines.append("- For each geometry family: at least one complex fixture and one invalid/pathological fixture.")
	lines.append("- Include explicit coverage for ambiguous / engine-dependent, degenerate but parseable, and format-limited validity cases.")
	lines.append("- Include explicit coverage for north pole, south pole, equator, and `EPSG:3857` scenarios.")
	lines.append("- For each edge-case category: at least one targeted fixture with explicit `risk_types` and assertions.")
	lines.append("- For each non-GeoJSON format (`GPKG`, `Shapefile`, `Parquet`, `GML`, `KML`, `CSV_WKT`, Feather/Arrow variants, `WKB`, `WKT`, `SQLite`, `FlatGeobuf`): at least one schema/encoding-focused or format-limited fixture.")

	lines.append("")
	lines.append("#### G) Phase 2 re-baselined gaps")
	lines.append("")
	lines.append("Use the live tree under `src/geocase/data/core/vector/` as the source of truth for this checklist.")
	lines.append("")
	lines.append("| Axis | Gap id | Current status | Planned case id(s) |")
	lines.append("|---|---|---|---|")
	for definition in PHASE2_GAP_DEFINITIONS:
		planned_case_ids = cast(list[str], definition["planned_cases"])
		planned_cases = ", ".join(f"`{case_id}`" for case_id in planned_case_ids)
		lines.append(
			f"| {definition['axis']} | `{definition['gap_id']}` | {_phase2_status(case_ids, definition)} | {planned_cases} |"
		)

	return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Generate vector coverage matrix markdown.")
	parser.add_argument(
		"--vector-root",
		type=Path,
		default=VECTOR_ROOT,
		help="Root directory containing vector case folders.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=None,
		help="Optional output markdown file path. If omitted, prints to stdout.",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()

	if not args.vector_root.exists():
		print(f"Vector root not found: {args.vector_root}")
		return 1

	entries = _load_vector_metadata(args.vector_root)
	if not entries:
		print("No vector case metadata found.")
		return 1

	markdown = _build_markdown(entries)

	if args.output is None:
		print(markdown, end="")
		return 0

	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(markdown)
	print(f"Wrote coverage matrix markdown to {args.output}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
