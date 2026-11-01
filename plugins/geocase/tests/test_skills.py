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
SKILLS = ["cases"]


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
