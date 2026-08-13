"""Guard the case-index parsing duplicated inside ``scripts/verify_dist.py``.

The release gate deliberately re-implements ``load_case_index`` instead of
importing ``geocase.catalog.loader``: importing the package pulls in the whole
dependency chain, which broke the gate on a clean CI runner. That duplication is
only safe while the two stay in agreement, which is what this test enforces.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from geocase.catalog.loader import load_case_index

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_DIST_PATH = REPO_ROOT / "scripts" / "verify_dist.py"
CASE_INDEX_PATH = REPO_ROOT / "src" / "geocase" / "metadata" / "case-index.yaml"


def _load_verify_dist():
    """Import ``scripts/verify_dist.py``, which is not on the package path."""
    spec = importlib.util.spec_from_file_location("_verify_dist", VERIFY_DIST_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_verify_dist"] = module
    spec.loader.exec_module(module)
    return module


def test_expected_case_files_matches_loader() -> None:
    """The gate's inlined parse must agree with the real loader, exactly."""
    verify_dist = _load_verify_dist()

    assert verify_dist._expected_case_files() == list(load_case_index(CASE_INDEX_PATH))


def test_expected_case_files_is_not_empty() -> None:
    """A silently-empty index would make every wheel content check vacuous."""
    verify_dist = _load_verify_dist()

    assert len(verify_dist._expected_case_files()) > 0


def test_verify_dist_does_not_import_geocase() -> None:
    """The gate must stay importable without the package being installed.

    This is the regression the duplication exists to prevent, so it is asserted
    on the source text rather than on behaviour -- the failure it guards against
    only reproduces in an environment where ``geocase`` is absent.
    """
    source = VERIFY_DIST_PATH.read_text()

    assert "from geocase" not in source
    assert "import geocase" not in source


def test_missing_index_raises_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mirrors ``load_case_index``: a missing index is an error, not an empty list."""
    verify_dist = _load_verify_dist()
    monkeypatch.setattr(
        verify_dist, "CASE_INDEX_PATH", REPO_ROOT / "does-not-exist.yaml"
    )

    with pytest.raises(FileNotFoundError):
        verify_dist._expected_case_files()
