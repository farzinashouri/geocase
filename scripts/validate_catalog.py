"""Validate GeoCase catalog metadata and suite integrity.

Checks:
- ``case-index.yaml`` can be loaded and referenced files exist.
- Indexed case metadata parses as ``CaseMetadata``.
- Duplicate case ids are rejected.
- Referenced case data files (primary/notes/preview/sidecars) exist.
- ``suite-index.yaml`` can be loaded and suites parse as ``SuiteMetadata``.
- Manifests in ``extended-manifests/`` parse, declare unique ids, and shadow
  no bundled case.
- ``case_order`` entries reference known case ids.
- Declared ``size_class`` matches the actual on-disk payload size.
- No ``*.yaml`` under ``data/core`` is missing from ``case-index.yaml``.
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
MANIFESTS_DIR = REPO_ROOT / "extended-manifests"

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.loader import (  # noqa: E402
	load_case_index,
	load_case_metadata,
	load_suite_index,
	load_suite_metadata,
)
from geocase.catalog.manifests import load_manifest  # noqa: E402
from geocase.catalog.registry import CaseRegistry  # noqa: E402
from geocase.catalog.suites import load_and_resolve_suite  # noqa: E402


#: Upper bound on a case's on-disk payload for each ``size_class``.
#:
#: ``SizeClass`` was a bare ``Literal`` with no byte meaning, and nothing checked
#: file sizes, so five ``tiny`` SpatiaLite fixtures sat at 6.7 MB each -- 93% of
#: the entire bundled catalog -- without anything noticing. These thresholds turn
#: "the metadata is lying" into a build failure.
#:
#: ``tiny`` is 512 KB rather than a snugger 256 KB deliberately: the largest
#: honest ``tiny`` case is a 240 KB SpatiaLite database, and SpatiaLite's
#: initialization footprint shifts between library versions. 512 KB keeps ~2x
#: headroom while staying 13x below the regression this guard exists to catch.
_SIZE_CLASS_MAX_BYTES: dict[str, int] = {
	"tiny": 512 * 1024,
	"small": 5 * 1024 * 1024,
	"medium": 50 * 1024 * 1024,
	# ``large`` is intentionally unbounded -- such cases belong in a remote
	# manifest rather than the wheel, which is enforced elsewhere.
}


class CatalogValidationError(Exception):
	"""Raised when catalog validation fails."""


def _case_payload_bytes(case_dir: Path, metadata: object) -> int:
	"""Return the total on-disk size of a case's data payload.

	Counts the primary file plus any sidecars (a Shapefile is several files),
	and ignores descriptive files such as ``case.yaml`` and ``notes.md``.
	"""
	files = metadata.files  # type: ignore[attr-defined]
	names = [files.primary, *files.sidecars]
	total = 0
	for name in names:
		if not name:
			continue
		resolved = case_dir / name
		if resolved.exists():
			total += resolved.stat().st_size
	return total


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
		missing_file = False
		for file_name in file_candidates:
			if not file_name:
				continue
			resolved = case_dir / file_name
			if not resolved.exists():
				errors.append(
					f"Case '{metadata.id}' references missing file: {resolved}"
				)
				missing_file = True

		# Only meaningful once every payload file is present.
		if not missing_file:
			limit = _SIZE_CLASS_MAX_BYTES.get(metadata.size_class)
			if limit is not None:
				payload = _case_payload_bytes(case_dir, metadata)
				if payload > limit:
					errors.append(
						f"Case '{metadata.id}' declares size_class "
						f"'{metadata.size_class}' but its payload is "
						f"{payload / 1024:.0f} KB, over the "
						f"{limit / 1024:.0f} KB limit"
					)

	if errors:
		raise CatalogValidationError("\n".join(errors))

	try:
		registry = CaseRegistry.from_index(case_index_path)
	except Exception as exc:
		raise CatalogValidationError(f"Failed to build case registry: {exc}") from exc

	return registry, entries


def _validate_no_orphan_case_metadata(
	case_index_path: Path,
	entries: list[str],
) -> None:
	"""Fail if a ``*.yaml`` under ``data/core`` is in no index.

	``build_case_index.py`` skips anything that does not parse as
	``CaseMetadata``, which is the right behaviour for discovery but means an
	empty stub is silently omitted from the index while still shipping in the
	wheel. ``raster/affine_transform_quirk/case.yaml`` did exactly that for
	months -- a single comment line, in no index, packaged anyway. This turns
	the next one into a build failure.
	"""
	package_root = case_index_path.parent.parent
	data_root = package_root / "data" / "core"
	if not data_root.exists():
		return

	indexed = {(package_root / rel).resolve() for rel in entries}
	orphans = sorted(
		path for path in data_root.rglob("*.yaml") if path.resolve() not in indexed
	)
	if not orphans:
		return

	listed = "\n".join(f"  {path.relative_to(package_root).as_posix()}" for path in orphans)
	raise CatalogValidationError(
		"Case metadata files present on disk but absent from case-index.yaml:\n"
		f"{listed}\n"
		"Either complete them (then run scripts/build_case_index.py) or delete "
		"them. An unindexed case still ships in the wheel."
	)


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


#: A manifest checksum that is deliberately not a checksum yet.
#:
#: Both bundled manifests use it: the archives they describe are not published,
#: so there is nothing to hash. Gating on it would fail the build over the exact
#: placeholder the v1.1 storage work exists to replace, so it is a warning --
#: loud enough to be seen, not loud enough to block.
_PLACEHOLDER_SHA256 = "replace_me"

#: A real SHA-256 digest is 64 hex characters.
_SHA256_LENGTH = 64


def _validate_manifests(
	manifests_dir: Path,
	registry: CaseRegistry,
) -> tuple[list[Path], list[str]]:
	"""Validate every manifest in *manifests_dir* against the bundled catalog.

	Manifests declare cases that live outside the wheel. Nothing here fetches
	anything -- the checks are that each file parses, that its case ids are
	unique within and across manifests, that none shadows a bundled case, and
	that each ``sha256`` is either a real digest or the known placeholder.

	Returns:
		The validated manifest paths, and any warnings worth printing.
	"""
	if not manifests_dir.exists():
		return [], []

	manifest_paths = sorted(manifests_dir.glob("*.yaml"))
	if not manifest_paths:
		return [], []

	errors: list[str] = []
	warnings: list[str] = []
	seen_case_ids: dict[str, str] = {}

	for manifest_path in manifest_paths:
		try:
			manifest = load_manifest(manifest_path)
		except Exception as exc:
			errors.append(f"Invalid manifest {manifest_path.name}: {exc}")
			continue

		for entry in manifest.cases:
			if entry.case_id in registry:
				errors.append(
					f"Manifest '{manifest.manifest_key}' declares case id "
					f"'{entry.case_id}', which is already bundled. A manifest "
					f"must not shadow packaged data."
				)
			owner = seen_case_ids.get(entry.case_id)
			if owner is not None:
				errors.append(
					f"Case id '{entry.case_id}' is declared by both "
					f"'{owner}' and '{manifest.manifest_key}'"
				)
			else:
				seen_case_ids[entry.case_id] = manifest.manifest_key

			if entry.sha256 == _PLACEHOLDER_SHA256:
				warnings.append(
					f"{manifest.manifest_key}/{entry.case_id}: sha256 is the "
					f"'{_PLACEHOLDER_SHA256}' placeholder (expected until the "
					f"archive is published)"
				)
			elif len(entry.sha256) != _SHA256_LENGTH:
				errors.append(
					f"Manifest '{manifest.manifest_key}' case '{entry.case_id}' "
					f"has sha256 '{entry.sha256}', which is neither a 64-character "
					f"digest nor the '{_PLACEHOLDER_SHA256}' placeholder"
				)

			if entry.bundled_analog and entry.bundled_analog not in registry:
				errors.append(
					f"Manifest '{manifest.manifest_key}' case '{entry.case_id}' "
					f"names bundled_analog '{entry.bundled_analog}', which is "
					f"not a bundled case id"
				)

	if errors:
		raise CatalogValidationError("\n".join(errors))

	return manifest_paths, warnings


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
		"--manifests-dir",
		type=Path,
		default=MANIFESTS_DIR,
		help="Directory of external manifest YAML files",
	)
	parser.add_argument(
		"--cases-only",
		action="store_true",
		help="Validate case metadata/index only (skip suites and manifests).",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()

	try:
		registry, case_entries = _validate_cases(args.case_index)
		_validate_no_orphan_case_metadata(args.case_index, case_entries)
		suite_entries: list[str] = []
		manifest_paths: list[Path] = []
		manifest_warnings: list[str] = []

		if not args.cases_only:
			suite_entries = _validate_suites(args.suite_index, registry)
			manifest_paths, manifest_warnings = _validate_manifests(
				args.manifests_dir, registry
			)
	except CatalogValidationError as exc:
		print("Catalog validation failed:")
		print(exc)
		return 1

	print("Catalog validation passed")
	print(f"- Indexed case metadata files: {len(case_entries)}")
	print(f"- Resolved unique case ids: {len(registry)}")
	if args.cases_only:
		print("- Suite validation: skipped (--cases-only)")
		print("- Manifest validation: skipped (--cases-only)")
	else:
		print(f"- Indexed suite files: {len(suite_entries)}")
		print(f"- Validated manifests: {len(manifest_paths)}")
	for warning in manifest_warnings:
		print(f"  warning: {warning}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
