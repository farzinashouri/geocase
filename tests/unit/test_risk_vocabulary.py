"""Tests for the risk-type vocabulary -- plan 40 phase 3.

``risk_types`` is the feature external reporters name as the most useful thing
in the package: it is a search index over failure modes, and it pointed at
``rotated_two_islands`` and ``landcover_ambiguous_zero_small`` **by name, in
seconds**. It was also, until this phase, ungated -- 124 distinct terms over
163 cases, 78 of them singletons, with only four terms checked against the
bytes anywhere. Everything else was indistinguishable from a typo, which is the
rule plan 27 wrote down and never enforced.

These tests are the enforcement: a term that is not in the canonical list is a
failure, and a canonical term that no case uses is also a failure, so the
vocabulary cannot rot in either direction.
"""

from __future__ import annotations

import pathlib

import yaml

import geocase
from geocase.catalog.risk_types import (
    RISK_TYPE_ALIASES,
    RISK_TYPE_DESCRIPTIONS,
    RISK_TYPES,
    canonical_risk_type,
    risk_type_family,
)

_DATA_ROOT = pathlib.Path(geocase.__file__).parent / "data" / "core"


def _declared_risk_types() -> dict[str, list[str]]:
    """Return ``{case id: risk_types}`` read from the raw YAML on disk.

    Deliberately not via the registry: the loader canonicalises, so reading
    through it would prove the alias layer works and say nothing about what is
    actually written in the files.
    """
    out: dict[str, list[str]] = {}
    for path in _DATA_ROOT.rglob("*.yaml"):
        raw = yaml.safe_load(path.read_text())
        if not isinstance(raw, dict) or "risk_types" not in raw:
            continue
        out[raw["id"]] = list(raw.get("risk_types") or [])
    return out


class TestTheCanonicalList:
    def test_every_declared_term_is_canonical(self) -> None:
        """A term outside the list is a typo until proven otherwise."""
        offenders: dict[str, list[str]] = {}
        for case_id, terms in _declared_risk_types().items():
            unknown = [t for t in terms if t not in RISK_TYPES]
            if unknown:
                offenders[case_id] = unknown
        assert offenders == {}, (
            "risk_types not in the canonical vocabulary "
            "(add to catalog/risk_types.py or fix the spelling): "
            f"{offenders}"
        )

    def test_no_canonical_term_is_unused(self) -> None:
        """A term no case carries is a promise the corpus does not keep."""
        used = {t for terms in _declared_risk_types().values() for t in terms}
        assert RISK_TYPES - used == set()

    def test_none_appears_nowhere(self) -> None:
        """``"none"`` is the absence of a risk type, spelled wrong (9 cases)."""
        assert "none" not in RISK_TYPES
        for case_id, terms in _declared_risk_types().items():
            assert "none" not in terms, f"{case_id} still declares 'none'"

    def test_format_comparison_is_not_a_risk(self) -> None:
        """It covered 37% of the corpus; a corpus-construction label, not a risk."""
        assert "format_comparison" not in RISK_TYPES
        for case_id, terms in _declared_risk_types().items():
            assert "format_comparison" not in terms, f"{case_id} still declares it"

    def test_format_comparison_survived_as_a_tag(self) -> None:
        """Moved, not deleted -- the 60 cases must still be selectable."""
        tagged = geocase.list_cases(tags_any=["format_comparison"])
        assert len(tagged) >= 60

    def test_every_term_has_a_description(self) -> None:
        """The descriptions feed the docs index, so they live with the data."""
        assert set(RISK_TYPE_DESCRIPTIONS) == RISK_TYPES
        for term, text in RISK_TYPE_DESCRIPTIONS.items():
            assert text.strip(), f"{term} has a blank description"


class TestTheSchemaAgrees:
    """``case.schema.yaml`` documents the same closed vocabulary the module owns."""

    def test_schema_enum_matches_the_canonical_list(self) -> None:
        schema = yaml.safe_load(
            (
                pathlib.Path(geocase.__file__).parent
                / "metadata"
                / "schemas"
                / "case.schema.yaml"
            ).read_text()
        )
        enum = schema["properties"]["risk_types"]["items"]["enum"]
        assert set(enum) == RISK_TYPES
        assert enum == sorted(enum)


class TestTheHierarchy:
    def test_families_are_slash_separated(self) -> None:
        for term in RISK_TYPES:
            assert term.count("/") <= 1, f"{term} is more than two levels deep"
            assert not term.startswith("/") and not term.endswith("/")

    def test_a_family_has_more_than_one_member(self) -> None:
        """A one-member family is a flat term wearing a prefix."""
        families: dict[str, set[str]] = {}
        for term in RISK_TYPES:
            if "/" in term:
                families.setdefault(term.split("/")[0], set()).add(term)
        singletons = {f: m for f, m in families.items() if len(m) < 2}
        assert singletons == {}

    def test_risk_type_family_reads_the_prefix(self) -> None:
        assert risk_type_family("crs/axis_order") == "crs"
        assert risk_type_family("dtype_drift") is None


class TestAliases:
    def test_every_alias_target_is_canonical(self) -> None:
        for old, new in RISK_TYPE_ALIASES.items():
            assert new in RISK_TYPES, f"alias {old} -> {new} is not canonical"

    def test_no_alias_shadows_a_canonical_term(self) -> None:
        assert RISK_TYPES & set(RISK_TYPE_ALIASES) == set()

    def test_canonical_risk_type_resolves_both_ways(self) -> None:
        assert canonical_risk_type("coordinate_order") == "crs/axis_order"
        assert canonical_risk_type("crs/axis_order") == "crs/axis_order"

    def test_canonical_risk_type_passes_through_the_unknown(self) -> None:
        """Resolution is not validation -- the schema enum is what rejects."""
        assert canonical_risk_type("not_a_real_term") == "not_a_real_term"


class TestSelectionKeepsWorking:
    """The v1.0 selector surface: an old string must still select."""

    def test_a_deprecated_alias_still_selects(self) -> None:
        by_alias = {
            c.id for c in geocase.list_cases(risk_types_any=["coordinate_order"])
        }
        by_canonical = {
            c.id for c in geocase.list_cases(risk_types_any=["crs/axis_order"])
        }
        assert by_alias
        assert by_alias <= by_canonical

    def test_a_family_prefix_selects_the_whole_family(self) -> None:
        family = {c.id for c in geocase.list_cases(risk_types_any=["crs"])}
        member = {c.id for c in geocase.list_cases(risk_types_any=["crs/axis_order"])}
        assert member
        assert member < family

    def test_registry_exposes_canonical_terms_only(self) -> None:
        """Aliases resolve at load, so no generated artifact sees an old term."""
        for case in geocase.list_cases():
            for term in case.risk_types:
                assert term in RISK_TYPES, f"{case.id} exposes {term!r}"


class TestTheReverseIndex:
    """Plan 40 phase 3.4 -- the mapping the reporter built with an ad-hoc Counter."""

    def test_risk_types_returns_term_to_case_ids(self) -> None:
        index = geocase.risk_types()
        assert set(index) == RISK_TYPES
        for term, ids in index.items():
            assert ids, f"{term} maps to no cases"
            assert ids == sorted(ids), f"{term} is not sorted"

    def test_the_index_agrees_with_the_selector(self) -> None:
        index = geocase.risk_types()
        term = "transform/rotated"
        assert set(index[term]) == {
            c.id for c in geocase.list_cases(risk_types_any=[term])
        }

    def test_risk_types_all_is_intersection_of_all(self) -> None:
        index = geocase.risk_types()
        pair = ["transform/rotated", "footprint/generation_error"]
        got = {c.id for c in geocase.list_cases(risk_types_all=pair)}
        assert got == set(index[pair[0]]) & set(index[pair[1]])
        assert got

    def test_risk_types_all_accepts_an_alias(self) -> None:
        got = {c.id for c in geocase.list_cases(risk_types_all=["coordinate_order"])}
        assert got == {
            c.id for c in geocase.list_cases(risk_types_all=["crs/axis_order"])
        }
