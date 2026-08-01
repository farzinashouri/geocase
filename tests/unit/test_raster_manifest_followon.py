"""Failing-first unit tests for Step 10 of the raster action plan.

These cover the *manifest-backed raster follow-on* described in
``docs/plans/archive/08-raster-action-plan.md`` (Step 10). The goal of that step is to
draw a clean boundary between the **small bundled structural fixtures** and the
**larger realistic EO scenes**, where the realistic scenes stay remote-only and
are described by a manifest instead of being shipped inside the package.

Concretely, Step 10 asks for:

* a raster scene manifest (the ``extended-manifests/satellite-scenes.yaml`` stub
  becomes a real manifest) that identifies which future raster cases remain
  **remote-only**,
* each remote scene **paired** with a small bundled analog so contributors can
  reason about "the big version of this fixture",
* no large EO scenes bundled inside ``src/geocase/data/`` (avoid package bloat),
* and transport/cache/fetch mechanics **deferred** to the manifest/storage work
  (the manifest only declares; nothing is downloaded or materialized here).

None of this exists yet, so every test in this module is expected to **fail**
until the manifest is authored and ``ManifestCaseEntry`` grows the pairing
field. The tests are written against existing public surfaces only:

* ``geocase.catalog.manifests.load_manifest`` / ``build_manifest_uri`` for
  manifest parsing and URI resolution,
* ``geocase.catalog.models.ManifestCaseEntry`` for the typed pairing field,
* ``geocase.catalog.registry`` for bundled-vs-remote distinction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import geocase.catalog.manifests as manifest_module
import geocase.catalog.models as models_module
from geocase.catalog.registry import CaseRegistry, get_registry

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "src" / "geocase"
_RASTER_MANIFEST = _REPO_ROOT / "extended-manifests" / "satellite-scenes.yaml"
_CASE_INDEX = _PACKAGE_ROOT / "metadata" / "case-index.yaml"
_BUNDLED_RASTER_DIR = _PACKAGE_ROOT / "data" / "core" / "raster"


# ---------------------------------------------------------------------------
# Expected Step 10 manifest shape
# ---------------------------------------------------------------------------

# The larger realistic EO scenes that should stay remote-only, each mapped to
# the small bundled fixture it is the realistic analog of. The analog ids must
# all already exist in the bundled catalog (shipped in earlier raster steps).
EXPECTED_RASTER_SCENES: dict[str, str] = {
    "optical_rgb_scene": "optical_rgb_small",
    "multispectral_s2_scene": "multispectral_s2_like_small",
    "sar_vv_scene": "sar_vv_small",
    "dem_scene": "dem_small",
    "landcover_scene": "landcover_small",
}

_RASTER_MANIFEST_KEY = "satellite-scenes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_attr(obj: object, name: str):
    value = getattr(obj, name, None)
    assert value is not None, (
        f"Expected {obj!r} to define `{name}` for the Step 10 raster "
        f"manifest follow-on (see docs/plans/archive/08-raster-action-plan.md, Step 10)"
    )
    return value


def _load_raster_manifest():
    load_manifest = _require_attr(manifest_module, "load_manifest")
    assert _RASTER_MANIFEST.exists(), (
        f"Expected a raster scene manifest at {_RASTER_MANIFEST} "
        f"(Step 10 turns the satellite-scenes stub into a real manifest)"
    )
    return load_manifest(_RASTER_MANIFEST)


def _entries_by_case_id() -> dict[str, object]:
    manifest = _load_raster_manifest()
    return {entry.case_id: entry for entry in manifest.cases}


# ---------------------------------------------------------------------------
# Manifest existence and shape
# ---------------------------------------------------------------------------


def test_raster_scene_manifest_loads_as_a_typed_manifest():
    manifest = _load_raster_manifest()
    assert manifest.manifest_key == _RASTER_MANIFEST_KEY
    # Remote scenes are fetched on demand; the storage block must declare a
    # concrete backend and base URI so storage work can resolve artifacts later.
    assert manifest.storage.storage_type in {"s3", "gcs", "azure", "https"}
    assert manifest.storage.base_uri


def test_raster_scene_manifest_declares_the_expected_remote_scenes():
    entries = _entries_by_case_id()
    for case_id in EXPECTED_RASTER_SCENES:
        assert case_id in entries, (
            f"Expected remote raster scene '{case_id}' in {_RASTER_MANIFEST.name}"
        )


# ---------------------------------------------------------------------------
# Pairing: each remote scene names its bundled analog
# ---------------------------------------------------------------------------


def test_manifest_case_entry_supports_a_bundled_analog_field():
    """`ManifestCaseEntry` should grow a typed `bundled_analog` pairing field."""
    entry_cls = _require_attr(models_module, "ManifestCaseEntry")
    fields = getattr(entry_cls, "model_fields", {})
    assert "bundled_analog" in fields, (
        "Step 10 pairs remote scenes with bundled fixtures via a "
        "`bundled_analog` field on ManifestCaseEntry"
    )


@pytest.mark.parametrize(
    "case_id, expected_analog", sorted(EXPECTED_RASTER_SCENES.items())
)
def test_remote_scene_is_paired_with_its_bundled_analog(case_id, expected_analog):
    entries = _entries_by_case_id()
    entry = entries.get(case_id)
    assert entry is not None, f"Remote scene '{case_id}' is not declared yet"

    analog = getattr(entry, "bundled_analog", None)
    assert analog == expected_analog, (
        f"Remote scene '{case_id}' should pair with bundled analog "
        f"'{expected_analog}', got {analog!r}"
    )


@pytest.mark.parametrize(
    "expected_analog", sorted(set(EXPECTED_RASTER_SCENES.values()))
)
def test_bundled_analog_exists_in_the_bundled_registry(expected_analog):
    registry = get_registry(reload=True)
    assert expected_analog in registry, (
        f"Bundled analog '{expected_analog}' must exist in the bundled catalog "
        f"so the remote scene has a small structural counterpart"
    )


# ---------------------------------------------------------------------------
# Remote-only: scenes are NOT bundled (no package bloat)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", sorted(EXPECTED_RASTER_SCENES))
def test_remote_scene_is_not_in_the_bundled_registry(case_id):
    registry = get_registry(reload=True)
    assert case_id not in registry, (
        f"Remote raster scene '{case_id}' must stay remote-only and not be "
        f"registered as a bundled case"
    )


@pytest.mark.parametrize("case_id", sorted(EXPECTED_RASTER_SCENES))
def test_remote_scene_artifacts_are_not_shipped_on_disk(case_id):
    """Transport is deferred to storage; the package must not contain the scene."""
    on_disk = _BUNDLED_RASTER_DIR / case_id
    assert not on_disk.exists(), (
        f"Remote raster scene '{case_id}' must not ship inside "
        f"src/geocase/data/core/raster/ (defer fetching to the storage layer)"
    )


def test_remote_scenes_declare_size_and_checksum_for_later_fetching():
    """The manifest must carry enough metadata for storage to fetch + verify."""
    entries = _entries_by_case_id()
    for case_id in EXPECTED_RASTER_SCENES:
        entry = entries[case_id]
        assert entry.relative_path, f"'{case_id}' needs a relative_path"
        assert entry.sha256, f"'{case_id}' needs a declared sha256 checksum"
        assert entry.byte_size and entry.byte_size > 0, (
            f"'{case_id}' should declare a positive byte_size"
        )


# ---------------------------------------------------------------------------
# URI resolution works without downloading anything
# ---------------------------------------------------------------------------


def test_remote_scene_uri_resolves_from_manifest_metadata():
    build_manifest_uri = _require_attr(manifest_module, "build_manifest_uri")
    manifest = _load_raster_manifest()
    entries = {entry.case_id: entry for entry in manifest.cases}

    entry = entries["optical_rgb_scene"]
    uri = build_manifest_uri(manifest, entry)

    base = manifest.storage.base_uri.rstrip("/")
    assert uri == f"{base}/{entry.relative_path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Bundled raster fixtures stay small (the whole point of the boundary)
# ---------------------------------------------------------------------------


def test_all_bundled_raster_fixtures_stay_small():
    """Large realistic scenes are remote; bundled raster fixtures stay tiny/small."""
    registry = get_registry(reload=True)
    oversized = [
        case.id
        for case in registry
        if case.category == "raster"
        and case.storage_class == "bundled"
        and case.size_class not in {"tiny", "small"}
    ]
    assert not oversized, (
        f"Bundled raster fixtures must stay tiny/small; oversized: {oversized}. "
        f"Move large realistic scenes to the remote satellite-scenes manifest."
    )


def test_remote_scenes_integrate_into_a_combined_registry_view():
    """`from_sources` should surface remote scenes alongside bundled cases."""
    from_sources = _require_attr(CaseRegistry, "from_sources")

    registry = from_sources(_CASE_INDEX, manifest_paths=[_RASTER_MANIFEST])
    ids = registry.list_ids()

    # Bundled analog and remote scene both visible in the combined view ...
    assert "optical_rgb_small" in ids
    assert "optical_rgb_scene" in ids
