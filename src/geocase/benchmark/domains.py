"""Domains (Plan 16 Phase 1).

A *domain* is a body of task content sharing one sandbox environment, one
prompt dependency sentence and one closed trap vocabulary. The instrument
itself — grading, taxonomy, runner — is domain-agnostic and always was; only
the task content is domain-specific.

``geo`` is the first and deepest domain. Its ``package_blurb`` is byte-identical
to the sentence the 51 committed bare prompts were generated with, and
``tests/benchmark/test_prompt_hashes.py`` holds that fact down.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from geocase.benchmark.taxonomy import TRAP_CATEGORIES_BY_DOMAIN

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIGS = REPO_ROOT / "configs"

GEO_DEPS = (
    "You may use the standard library plus any of: shapely 2.1, pyproj 3.7, "
    "rasterio 1.4, numpy, scikit-learn."
)
STDLIB_DEPS = "You may use the Python standard library only — no third-party packages."


@dataclass(frozen=True)
class Domain:
    name: str
    requirements: Path
    package_blurb: str
    trap_categories: frozenset[str]

    @property
    def packages(self) -> frozenset[str]:
        """Distributions the domain's sandbox provides, by requirement name."""
        names = set()
        for line in self.requirements.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                names.add(line.split("==")[0].split(">=")[0].split("[")[0].strip())
        return frozenset(names)


DOMAINS: dict[str, Domain] = {
    "geo": Domain(
        name="geo",
        requirements=CONFIGS / "sandbox-requirements.txt",
        package_blurb=GEO_DEPS,
        trap_categories=TRAP_CATEGORIES_BY_DOMAIN["geo"],
    ),
    "stdlib": Domain(
        name="stdlib",
        requirements=CONFIGS / "sandbox-requirements-stdlib.txt",
        package_blurb=STDLIB_DEPS,
        trap_categories=TRAP_CATEGORIES_BY_DOMAIN["stdlib"],
    ),
}

DEFAULT_DOMAIN = "geo"


def get_domain(name: str) -> Domain:
    try:
        return DOMAINS[name]
    except KeyError:
        raise KeyError(f"unknown domain {name!r}; known: {sorted(DOMAINS)}") from None
