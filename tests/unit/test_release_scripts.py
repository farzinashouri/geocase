"""The release scripts behind the one-click pipeline (Plan 50, issue #52).

`prepare_release.py` bumps the version and dates the changelog,
`changelog_section.py` extracts release notes, and `smoke_release.py` checks an
installed geocase. They live in `scripts/`, outside the package, so they are
loaded by path like `verify_dist.py`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

import geocase

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"_{name}", REPO_ROOT / "scripts" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"_{name}"] = module
    spec.loader.exec_module(module)
    return module


CHANGELOG = """# Changelog

Intro text.

## [Unreleased]

### Added

- A new case.

## [1.1.0] — 2026-09-27

### Added — the `array` extra

- numpy extra.

## [1.0.0] — 2026-09-05

- First release.
"""

PYPROJECT = (
    '[project]\nname = "geocase"\nversion = "1.1.0"\n\n[tool.x]\nversion = "9"\n'
)


# --- prepare_release -------------------------------------------------------


def test_bump_version_changes_only_the_project_version() -> None:
    prepare = _load("prepare_release")
    out = prepare.bump_version(PYPROJECT, "1.2.0")
    assert 'version = "1.2.0"' in out
    assert 'version = "9"' in out  # other tables untouched


@pytest.mark.parametrize("version", ["1.1.0", "1.0.9", "1.1.0rc1", "banana"])
def test_bump_version_rejects_non_increasing_or_invalid(version: str) -> None:
    prepare = _load("prepare_release")
    with pytest.raises(ValueError):
        prepare.bump_version(PYPROJECT, version)


def test_bump_version_accepts_an_rc_of_the_next_version() -> None:
    prepare = _load("prepare_release")
    assert 'version = "1.2.0rc1"' in prepare.bump_version(PYPROJECT, "1.2.0rc1")


def test_release_changelog_dates_the_unreleased_section() -> None:
    prepare = _load("prepare_release")
    out = prepare.release_changelog(CHANGELOG, "1.2.0", "2026-10-01")
    assert "## [1.2.0] — 2026-10-01\n\n### Added\n\n- A new case." in out
    assert "[Unreleased]" not in out
    assert "## [1.1.0] — 2026-09-27" in out


def test_release_changelog_needs_an_unreleased_section() -> None:
    prepare = _load("prepare_release")
    without = CHANGELOG.replace("## [Unreleased]\n\n### Added\n\n- A new case.\n\n", "")
    with pytest.raises(ValueError, match="Unreleased"):
        prepare.release_changelog(without, "1.2.0", "2026-10-01")


def test_release_changelog_rejects_an_empty_unreleased_section() -> None:
    prepare = _load("prepare_release")
    empty = CHANGELOG.replace("### Added\n\n- A new case.\n\n", "")
    with pytest.raises(ValueError, match="empty"):
        prepare.release_changelog(empty, "1.2.0", "2026-10-01")


def test_prepare_main_writes_both_files(tmp_path: Path) -> None:
    prepare = _load("prepare_release")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    assert prepare.main(["1.2.0", "--date", "2026-10-01"], root=tmp_path) == 0
    assert 'version = "1.2.0"' in (tmp_path / "pyproject.toml").read_text()
    assert "## [1.2.0] — 2026-10-01" in (tmp_path / "CHANGELOG.md").read_text()


# --- changelog_section -----------------------------------------------------


def test_changelog_section_returns_the_body_only() -> None:
    section = _load("changelog_section")
    assert section.section(CHANGELOG, "1.1.0") == (
        "### Added — the `array` extra\n\n- numpy extra."
    )


def test_changelog_section_last_section_runs_to_the_end() -> None:
    section = _load("changelog_section")
    assert section.section(CHANGELOG, "1.0.0") == "- First release."


def test_changelog_section_missing_version_raises() -> None:
    section = _load("changelog_section")
    with pytest.raises(ValueError, match="1.9.0"):
        section.section(CHANGELOG, "1.9.0")


def test_real_changelog_has_the_current_version() -> None:
    section = _load("changelog_section")
    text = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert section.section(text, geocase.__version__)


# --- smoke_release ---------------------------------------------------------


def _by_name(checks: list) -> dict:
    return {c.name: c for c in checks}


def test_smoke_array_mode_passes_on_this_install() -> None:
    pytest.importorskip("numpy")
    smoke = _load("smoke_release")
    checks = smoke.run_checks(geocase.__version__, "array")
    failed = [c for c in checks if not c.ok]
    assert not failed, failed
    assert {"version", "cases", "data file", "pytest plugin", "geocase.raster"} <= set(
        _by_name(checks)
    )


def test_smoke_wrong_version_fails() -> None:
    smoke = _load("smoke_release")
    checks = _by_name(smoke.run_checks("0.0.1", "array"))
    assert not checks["version"].ok


def test_smoke_core_mode_fails_when_numpy_is_installed() -> None:
    pytest.importorskip("numpy")
    smoke = _load("smoke_release")
    checks = _by_name(smoke.run_checks(geocase.__version__, "core"))
    assert not checks["no numpy in core"].ok


def test_smoke_report_and_exit_code() -> None:
    smoke = _load("smoke_release")
    checks = [smoke.Check("a", True, "fine"), smoke.Check("b", False, "broken")]
    report = smoke.report(checks, "1.2.0", "core")
    assert "| a | ✅ | fine |" in report
    assert "| b | ❌ | broken |" in report
    assert smoke.exit_code(checks) == 1
    assert smoke.exit_code(checks[:1]) == 0
