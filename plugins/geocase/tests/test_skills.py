"""Tests for the plugin's skills (Plan 55 Phases 2-4).

Each skill is a ``skills/<name>/SKILL.md``. These tests pin the parts that can
rot silently: the frontmatter, the helper subcommands a skill names, and the
risk terms it quotes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import geocase

PLUGIN = Path(__file__).resolve().parents[1]
HELPER = (PLUGIN / "scripts" / "catalog.py").read_text(encoding="utf-8")
SKILLS = ["cases", "test", "explain"]


def read_skill(name: str) -> tuple[dict[str, str], str]:
    text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    assert match, f"{name}: no frontmatter"
    front: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        front[key.strip()] = value.strip()
    return front, match.group(2)


@pytest.mark.parametrize("name", SKILLS)
def test_frontmatter_has_name_and_description(name: str) -> None:
    front, _ = read_skill(name)
    assert front["name"] == name
    assert front["description"]


@pytest.mark.parametrize("name", SKILLS)
def test_named_helper_subcommands_exist(name: str) -> None:
    _, body = read_skill(name)
    used = set(re.findall(r"catalog\.py (\w+)", body))
    assert used, "skill never runs the helper"
    for sub in used:
        assert f'add_parser("{sub}"' in HELPER, f"{sub} is not a helper subcommand"


@pytest.mark.parametrize("name", SKILLS)
def test_quoted_risk_terms_are_real(name: str) -> None:
    _, body = read_skill(name)
    terms = set(geocase.risk_types())
    families = {t.split("/")[0] for t in terms}
    quoted = re.findall(r"--risk (\S+)", body)
    for term in quoted:
        assert term in terms or term in families, f"unknown risk term {term}"


def test_cases_skill_ends_with_geocase_select() -> None:
    _, body = read_skill("cases")
    assert "geocase_select(" in body


# --- the `test` skill (Plan 55 Phase 3) -------------------------------------

PINNED_FIXTURES = {"geocase", "geocase_case", "geocase_cases", "geocase_registry"}
PINNED_MARKERS = {"geocase_case", "geocase_suite", "geocase_select", "remote"}


def python_blocks(body: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", body, re.DOTALL)


def test_test_skill_frontmatter() -> None:
    front, _ = read_skill("test")
    assert front["name"] == "test"
    assert front["description"]


def test_test_skill_uses_only_pinned_markers_and_fixtures() -> None:
    _, body = read_skill("test")
    markers = set(re.findall(r"pytest\.mark\.(geocase\w*|remote)", body))
    assert markers, "skill names no marker"
    assert markers <= PINNED_MARKERS
    fixtures = set(re.findall(r"\b(geocase_(?:case|cases|registry))\b", body))
    assert fixtures <= PINNED_FIXTURES


def test_test_skill_assertions_exist() -> None:
    import geocase.assertions as assertions

    _, body = read_skill("test")
    named = set(re.findall(r"\b(assert_[a-z_]+)\b", body))
    assert named, "skill names no assertion"
    for name in named:
        assert hasattr(assertions, name), f"geocase.assertions has no {name}"


def test_test_skill_uses_the_cases_skill_helper() -> None:
    _, body = read_skill("test")
    assert "catalog.py" in body or "cases" in body


def test_test_skill_never_edits_function_under_test() -> None:
    _, body = read_skill("test")
    assert "never edit" in body.lower()


def test_explain_skill_frontmatter() -> None:
    front, _ = read_skill("explain")
    assert front["name"] == "explain"
    assert front["description"]


def test_explain_skill_reads_notes_through_the_helper() -> None:
    _, body = read_skill("explain")
    assert "catalog.py case" in body
    assert "site-packages" not in body


def test_explain_skill_reports_known_divergences_as_known() -> None:
    _, body = read_skill("explain")
    assert "known_divergences" in body
    assert "known" in body.lower()


def test_explain_skill_finds_case_id_in_test_id() -> None:
    _, body = read_skill("explain")
    assert "test_x[<case_id>]" in body


def test_explain_skill_applies_fix_only_if_asked() -> None:
    _, body = read_skill("explain")
    assert "only if" in body.lower()


def test_helper_case_output_carries_known_divergences() -> None:
    meta = geocase.get_case(geocase.list_cases()[0].id)
    assert "known_divergences" in meta.model_dump(mode="json")


# --- sandbox and install offer (Plan 56 Phase 3) ----------------------------

ENV_HELPER = (PLUGIN / "scripts" / "env.py").read_text(encoding="utf-8")
SANDBOX_HELPER = (PLUGIN / "scripts" / "sandbox.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["cases", "explain"])
def test_read_only_skills_offer_the_sandbox_on_exit_3(name: str) -> None:
    _, body = read_skill(name)
    low = body.lower()
    assert "sandbox.py create" in body
    assert "exit" in low and "3" in body
    assert "does not touch" in low
    assert "only after" in low
    assert "sandbox python" in low
    for sub in re.findall(r"sandbox\.py (\w+)", body):
        assert f'add_parser("{sub}"' in SANDBOX_HELPER


def test_cases_skill_offers_the_install_after_a_sandbox_answer() -> None:
    _, body = read_skill("cases")
    low = body.lower()
    assert "env.py detect --version" in body
    assert "manifest" in low
    assert "only after" in low
    assert "sandbox version" in low


def test_test_skill_skips_the_sandbox() -> None:
    _, body = read_skill("test")
    assert "sandbox.py create" not in body
    assert "env.py detect --version" in body
    low = body.lower()
    assert "user's environment" in low
    assert "manifest" in low


@pytest.mark.parametrize("name", SKILLS)
def test_skills_refuse_when_not_installable(name: str) -> None:
    _, body = read_skill(name)
    low = body.lower()
    assert "installable" in low
    assert "reason" in low
    assert "install nothing" in low
    assert '"detect"' in ENV_HELPER or "detect" in ENV_HELPER


def test_test_skill_template_collects(tmp_path: Path) -> None:
    """Fill the template for docs Example A and collect it with pytest."""
    import subprocess
    import sys

    _, body = read_skill("test")
    blocks = [b for b in python_blocks(body) if "<function>" in b]
    assert blocks, "skill has no template block with <function>"
    import textwrap

    filled = (
        textwrap.dedent(blocks[0])
        .replace("<module>", "gdal_footprint")
        .replace("<function>", "geotiff_footprint_to_geojson")
        .replace("<selector>", 'category="raster"')
    )
    (tmp_path / "gdal_footprint.py").write_text(
        "def geotiff_footprint_to_geojson(src, dst):\n    return dst\n",
        encoding="utf-8",
    )
    (tmp_path / "test_generated.py").write_text(filled, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "error" not in result.stdout.lower()
