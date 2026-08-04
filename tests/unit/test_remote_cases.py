"""Tests for manifest-backed (remote) case ids — Step 14.

No transport: nothing here downloads anything. The behaviour under test is that
a manifest id is *reachable* (it resolves through the registry) and *honest*
(asking for its data fails with an error that says where the data is, from
every path a user can reach it by).
"""

from pathlib import Path

import pytest
import yaml

import geocase
from geocase.catalog import roots
from geocase.catalog.errors import RemoteCaseUnavailableError
from geocase.catalog.registry import (
    MANIFESTS_ENV_VAR,
    CaseRegistry,
    get_registry,
    manifest_paths_from_env,
    reset_registry,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_DIR = _REPO_ROOT / "extended-manifests"
_PUBLIC_MANIFEST = _MANIFEST_DIR / "public-extended.yaml"
_CASE_INDEX = _REPO_ROOT / "src" / "geocase" / "metadata" / "case-index.yaml"

_REMOTE_ID = "coastal_scene_small"


@pytest.fixture()
def remote_registry(monkeypatch):
    """Point the default registry at the bundled sample manifest."""
    monkeypatch.setenv(MANIFESTS_ENV_VAR, str(_PUBLIC_MANIFEST))
    reset_registry()
    yield get_registry()
    monkeypatch.delenv(MANIFESTS_ENV_VAR, raising=False)
    reset_registry()


# ===================================================================
# 14.1 — GEOCASE_MANIFESTS wiring
# ===================================================================


class TestManifestEnvVar:
    """``GEOCASE_MANIFESTS`` is read at call time, not at import time."""

    def test_unset_variable_yields_no_manifest_paths(self, monkeypatch):
        """Test the default install sees no manifests."""
        monkeypatch.delenv(MANIFESTS_ENV_VAR, raising=False)
        assert manifest_paths_from_env() == []

    def test_separated_entries_are_resolved_in_order(self):
        """Test several manifest files can be listed at once."""
        import os

        value = os.pathsep.join(
            [str(_PUBLIC_MANIFEST), str(_MANIFEST_DIR / "satellite-scenes.yaml")]
        )
        assert manifest_paths_from_env(value) == [
            _PUBLIC_MANIFEST,
            _MANIFEST_DIR / "satellite-scenes.yaml",
        ]

    def test_a_directory_expands_to_its_yaml_files(self):
        """Test pointing at a manifest directory picks up every manifest."""
        assert manifest_paths_from_env(str(_MANIFEST_DIR)) == sorted(
            _MANIFEST_DIR.glob("*.yaml")
        )

    def test_blank_entries_are_ignored(self):
        """Test a trailing separator does not produce an empty path."""
        assert manifest_paths_from_env(f"{_PUBLIC_MANIFEST}::") == [_PUBLIC_MANIFEST]

    def test_registry_picks_up_manifest_ids(self, remote_registry):
        """Test the env var makes manifest ids reachable through get_registry."""
        assert _REMOTE_ID in remote_registry
        assert _REMOTE_ID in remote_registry.list_ids()

    def test_registry_rebuilds_when_the_variable_changes(self, monkeypatch):
        """Test a monkeypatched variable is not defeated by the singleton.

        Reading the variable inside ``get_registry`` is only half the fix; the
        resolved sources have to be part of the cache key too, or the first
        call's registry is handed back unchanged.
        """
        monkeypatch.delenv(MANIFESTS_ENV_VAR, raising=False)
        reset_registry()
        bundled_only = get_registry()
        assert not bundled_only.list_remote_ids()

        monkeypatch.setenv(MANIFESTS_ENV_VAR, str(_PUBLIC_MANIFEST))
        assert get_registry().list_remote_ids() == [
            "coastal_scene_small",
            "utm_boundary_scene",
        ]

        monkeypatch.delenv(MANIFESTS_ENV_VAR, raising=False)
        assert get_registry().list_remote_ids() == []
        reset_registry()

    def test_a_missing_manifest_path_names_itself(self, monkeypatch, tmp_path):
        """Test a typo in the variable fails loudly rather than silently."""
        missing = tmp_path / "not-a-manifest.yaml"
        monkeypatch.setenv(MANIFESTS_ENV_VAR, str(missing))
        reset_registry()

        with pytest.raises(FileNotFoundError, match="not-a-manifest.yaml"):
            get_registry()

        monkeypatch.delenv(MANIFESTS_ENV_VAR, raising=False)
        reset_registry()


# ===================================================================
# 14.2 — the CaseRegistry asymmetry
# ===================================================================


class TestRegistryRemoteLookup:
    """Manifest ids are visible, typed correctly, and never faked."""

    def test_remote_ids_are_listed_separately(self, remote_registry):
        """Test list_remote_ids reports exactly the manifest-backed ids."""
        assert remote_registry.list_remote_ids() == [
            "coastal_scene_small",
            "utm_boundary_scene",
        ]

    def test_is_remote_distinguishes_bundled_from_manifest_ids(self, remote_registry):
        """Test is_remote answers for both kinds of id."""
        bundled_id = remote_registry.list_cases()[0].id

        assert remote_registry.is_remote(_REMOTE_ID)
        assert not remote_registry.is_remote(bundled_id)
        assert not remote_registry.is_remote("no_such_case_id")

    def test_list_cases_stays_case_metadata_only(self, remote_registry):
        """Test manifest entries are not forced into list_cases.

        ``ManifestCaseEntry`` is not ``CaseMetadata``; including it would be a
        type lie for every caller that reads ``.category`` or ``.assertions``.
        """
        listed = {case.id for case in remote_registry.list_cases()}
        iterated = {case.id for case in remote_registry}

        assert _REMOTE_ID not in listed
        assert _REMOTE_ID not in iterated
        assert len(remote_registry) == len(listed) + 2

    def test_get_manifest_returns_the_owning_manifest(self, remote_registry):
        """Test a remote id resolves to the manifest that lists it."""
        assert remote_registry.get_manifest(_REMOTE_ID).manifest_key == (
            "public-extended"
        )

    def test_get_manifest_entry_returns_the_artifact_record(self, remote_registry):
        """Test the entry carries the path, version, and checksum."""
        entry = remote_registry.get_manifest_entry(_REMOTE_ID)

        assert entry.case_id == _REMOTE_ID
        assert entry.relative_path == "coastal_scene_small.zip"
        assert entry.version

    def test_get_manifest_rejects_a_bundled_id(self, remote_registry):
        """Test asking for a bundled case's manifest is an error, not None."""
        bundled_id = remote_registry.list_cases()[0].id

        with pytest.raises(KeyError):
            remote_registry.get_manifest(bundled_id)


class TestRemoteCaseUnavailableError:
    """The error that replaces a bare KeyError for manifest ids."""

    def test_get_raises_it_for_a_manifest_id(self, remote_registry):
        """Test registry.get refuses a remote id explicitly."""
        with pytest.raises(RemoteCaseUnavailableError):
            remote_registry.get(_REMOTE_ID)

    def test_it_is_a_key_error(self, remote_registry):
        """Test existing `except KeyError` callers keep working."""
        with pytest.raises(KeyError):
            remote_registry.get(_REMOTE_ID)

    def test_the_message_names_the_artifact_uri(self, remote_registry):
        """Test the message says where the data is, not just that it is absent."""
        with pytest.raises(RemoteCaseUnavailableError) as excinfo:
            remote_registry.get(_REMOTE_ID)

        message = str(excinfo.value)
        assert _REMOTE_ID in message
        assert "public-extended" in message
        assert "https://example.org/geocase/public/coastal_scene_small.zip" in message
        assert excinfo.value.case_id == _REMOTE_ID
        assert excinfo.value.manifest_key == "public-extended"

    def test_an_unknown_id_still_raises_a_plain_key_error(self, remote_registry):
        """Test the new error is reserved for ids that really are catalogued."""
        with pytest.raises(KeyError) as excinfo:
            remote_registry.get("no_such_case_id")

        assert not isinstance(excinfo.value, RemoteCaseUnavailableError)


# ===================================================================
# 14.3 — the same error from the load path
# ===================================================================


class TestRemoteErrorFromBothPaths:
    """A remote id must fail the same way through the API and the plugin.

    ``case_roots_by_id`` is built from ``case-index.yaml`` alone, so a manifest
    id misses it and would raise an internal-sounding "No case root found" —
    defeating the actionable error above. This is why 14.2 and 14.3 shipped
    together.
    """

    def test_load_case_raises_the_actionable_error(self, remote_registry):
        """Test the public load path reports the URI."""
        with pytest.raises(RemoteCaseUnavailableError) as excinfo:
            geocase.load_case(_REMOTE_ID)

        assert "coastal_scene_small.zip" in str(excinfo.value)

    def test_materialize_case_raises_the_actionable_error(self, remote_registry):
        """Test the plugin's load path reports the URI too.

        The plugin reaches ``materialize_case`` with metadata in hand, so it
        bypasses ``registry.get()`` and needs its own check.
        """
        meta = remote_registry.list_cases()[0].model_copy(update={"id": _REMOTE_ID})

        with pytest.raises(RemoteCaseUnavailableError) as excinfo:
            roots.materialize_case(meta)

        assert "No case root found" not in str(excinfo.value)
        assert "coastal_scene_small.zip" in str(excinfo.value)

    def test_a_bundled_id_with_no_root_still_says_so(self, remote_registry):
        """Test the internal error survives for the case it was written for."""
        meta = remote_registry.list_cases()[0].model_copy(update={"id": "ghost_case"})

        with pytest.raises(KeyError, match="No case root found"):
            roots.materialize_case(meta)

    def test_show_case_describes_a_remote_case_instead_of_refusing_it(
        self, remote_registry
    ):
        """Test show_case reports remote state — the reason Step 15 came first."""
        text = geocase.show_case(_REMOTE_ID)

        assert _REMOTE_ID in text
        assert "public-extended" in text
        assert "not fetched" in text
        assert "https://example.org/geocase/public/coastal_scene_small.zip" in text


class TestResetRegistryClearsTheRootCache:
    """``reset_registry`` owns both caches over the same catalog."""

    def test_reset_clears_the_case_root_cache(self):
        """Test the lru_cache is not left warm behind a reset registry."""
        roots.case_roots_by_id()
        assert roots.case_roots_by_id.cache_info().currsize == 1

        reset_registry()

        assert roots.case_roots_by_id.cache_info().currsize == 0


# ===================================================================
# Collisions
# ===================================================================


class TestManifestCollisions:
    """A manifest may not shadow or duplicate a case id."""

    def test_a_manifest_id_colliding_with_a_bundled_id_is_rejected(self, tmp_path):
        """Test a manifest cannot shadow bundled data."""
        bundled_id = CaseRegistry.from_index(_CASE_INDEX).list_cases()[0].id
        manifest_path = tmp_path / "colliding.yaml"
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "manifest_key": "colliding",
                    "title": "Colliding",
                    "schema_version": "1.0",
                    "storage": {
                        "storage_type": "https",
                        "base_uri": "https://example.org/geocase/public",
                    },
                    "cases": [
                        {
                            "case_id": bundled_id,
                            "version": "1.0.0",
                            "relative_path": f"{bundled_id}.zip",
                            "sha256": "abc123",
                        }
                    ],
                }
            )
        )

        with pytest.raises(ValueError, match="collides"):
            CaseRegistry.from_sources(_CASE_INDEX, manifest_paths=[manifest_path])
