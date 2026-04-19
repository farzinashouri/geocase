"""Validate GeoCase catalog metadata and suite integrity.

Checks:
- ``case-index.yaml`` can be loaded and referenced files exist.
- Indexed case metadata parses as ``CaseMetadata``.
- Duplicate case ids are rejected.
- Referenced case data files (primary/notes/preview/sidecars) exist.
- ``suite-index.yaml`` can be loaded and suites parse as ``SuiteMetadata``.
- ``case_order`` entries reference known case ids.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "geocase"
METADATA_DIR = PACKAGE_ROOT / "metadata"
CASE_INDEX_PATH = METADATA_DIR / "case-index.yaml"
SUITE_INDEX_PATH = METADATA_DIR / "suite-index.yaml"

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.loader import (  # noqa: E402
	load_case_index,
	load_case_metadata,
	load_suite_index,
	load_suite_metadata,
)
from geocase.catalog.registry import CaseRegistry  # noqa: E402
from geocase.catalog.suites import load_and_resolve_suite  # noqa: E402


class CatalogValidationError(Exception):
	"""Raised when catalog validation fails."""


def _validate_case_index_structure(case_index_path: Path) -> list[str]:
	if not case_index_path.exists():
		raise CatalogValidationError(f"Missing case index: {case_index_path}")

	try:
		entries = load_case_index(case_index_path)
	except Exception as exc:
		raise CatalogValidationError(
			f"Failed to parse case index at {case_index_path}: {exc}"
		) from exc

	if not entries:
		raise CatalogValidationError("Case index is empty")

	duplicates = sorted({p for p in entries if entries.count(p) > 1})
	if duplicates:
		dup_text = ", ".join(duplicates)
		raise CatalogValidationError(f"Duplicate case-index paths found: {dup_text}")

	return entries


def _validate_cases(case_index_path: Path) -> tuple[CaseRegistry, list[str]]:
	entries = _validate_case_index_structure(case_index_path)
	src_root = case_index_path.parent.parent

	errors: list[str] = []

	for rel_path in entries:
		case_path = src_root / rel_path
		if not case_path.exists():
			errors.append(f"Missing case metadata file: {case_path}")
			continue

		try:
			metadata = load_case_metadata(case_path)
		except Exception as exc:
			errors.append(f"Invalid case metadata {case_path}: {exc}")
			continue

		case_dir = case_path.parent
		file_candidates = [
			metadata.files.primary,
			metadata.files.notes,
			metadata.files.preview,
			*metadata.files.sidecars,
		]
		for file_name in file_candidates:
			if not file_name:
				continue
			resolved = case_dir / file_name
			if not resolved.exists():
				errors.append(
					f"Case '{metadata.id}' references missing file: {resolved}"
				)

	if errors:
		raise CatalogValidationError("\n".join(errors))

	try:
		registry = CaseRegistry.from_index(case_index_path)
	except Exception as exc:
		raise CatalogValidationError(f"Failed to build case registry: {exc}") from exc

	return registry, entries


def _validate_suite_index_structure(suite_index_path: Path) -> list[str]:
	if not suite_index_path.exists():
		raise CatalogValidationError(f"Missing suite index: {suite_index_path}")

	try:
		entries = load_suite_index(suite_index_path)
	except Exception as exc:
		raise CatalogValidationError(
			f"Failed to parse suite index at {suite_index_path}: {exc}"
		) from exc

	if not entries:
		raise CatalogValidationError("Suite index is empty")

	duplicates = sorted({p for p in entries if entries.count(p) > 1})
	if duplicates:
		dup_text = ", ".join(duplicates)
		raise CatalogValidationError(f"Duplicate suite-index paths found: {dup_text}")

	return entries


def _validate_suites(
	suite_index_path: Path,
	registry: CaseRegistry,
) -> list[str]:
	entries = _validate_suite_index_structure(suite_index_path)
	errors: list[str] = []
	suite_base = suite_index_path.parent

	for rel_path in entries:
		suite_path = (suite_base / rel_path).resolve()
		if not suite_path.exists():
			errors.append(f"Missing suite file: {suite_path}")
			continue

		try:
			suite_meta = load_suite_metadata(suite_path)
		except Exception as exc:
			errors.append(f"Invalid suite metadata {suite_path}: {exc}")
			continue

		unknown_case_ids = [
			case_id for case_id in suite_meta.case_order if case_id not in registry
		]
		if unknown_case_ids:
			errors.append(
				f"Suite '{suite_meta.suite_key}' has unknown case_order ids: "
				f"{', '.join(unknown_case_ids)}"
			)

		try:
			resolved = load_and_resolve_suite(suite_path, registry)
		except Exception as exc:
			errors.append(
				f"Suite '{suite_meta.suite_key}' failed to resolve against registry: {exc}"
			)
			continue

		if len(resolved) == 0:
			errors.append(f"Suite '{suite_meta.suite_key}' resolved to zero cases")

	if errors:
		raise CatalogValidationError("\n".join(errors))

	return entries


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Validate GeoCase case and suite catalog metadata."
	)
	parser.add_argument(
		"--case-index",
		type=Path,
		default=CASE_INDEX_PATH,
		help="Path to case-index.yaml",
	)
	parser.add_argument(
		"--suite-index",
		type=Path,
		default=SUITE_INDEX_PATH,
		help="Path to suite-index.yaml",
	)
	parser.add_argument(
		"--cases-only",
		action="store_true",
		help="Validate case metadata/index only (skip suites).",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()

	try:
		registry, case_entries = _validate_cases(args.case_index)
		suite_entries: list[str] = []

		if not args.cases_only:
			suite_entries = _validate_suites(args.suite_index, registry)
	except CatalogValidationError as exc:
		print("Catalog validation failed:")
		print(exc)
		return 1

	print("Catalog validation passed")
	print(f"- Indexed case metadata files: {len(case_entries)}")
	print(f"- Resolved unique case ids: {len(registry)}")
	if args.cases_only:
		print("- Suite validation: skipped (--cases-only)")
	else:
		print(f"- Indexed suite files: {len(suite_entries)}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
