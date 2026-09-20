"""Generate the numeric-boundary vector fixtures -- plan 44 phase 2.

Round 6 found GDAL writing coordinates in ``[1e-14, 1e-13)`` as ``0`` -- both
the WKT and the GeoJSON writers, no error, no warning, relative error 1.0. It
found it by **luck**: ``precision_loss_geojson_roundtrip`` carries three points
and the third happens to sit at ``1e-14``, the single magnitude where the
significant digit lands on the one string position ``intelliround``
(``ogr/ogrutils.cpp:161-169``) does not test.

A case chosen for "very small values near zero" is not the same as a case
chosen against the *formatter*, and the difference is the whole finding. These
seven cases are the designed version:

* two on **significant digits** -- a value that round-trips in 15 and one that
  needs 17, which is what the writer's default of 15 decimal places cannot hold;
* two on the **patterns ``intelliround`` special-cases** -- a decimal expansion
  ending in five ``0``s and one ending in five ``9``s. ``0.000000010000001``
  loses its tail through exactly this path;
* three **bracketing the magnitude class** at ``1e-13``, ``1e-14`` and
  ``1e-15``, so the boundary is bounded on both sides rather than hit once. A
  consumer that fails only the middle case has reproduced the GDAL class
  exactly; one that fails all three has a different bug.

Single-variable per plan 40's control principle: **one feature per case**, so a
failure names the property rather than a file. Each case ships the coordinate
it must round-trip to in ``assertions.expected_roundtrip_coordinates`` (plan 44
phase 2.2) -- a typed field, not ``params``, because "did the value survive?"
is only answerable against a declared answer and ``params`` has no whitelist.

Usage::

    python scripts/generate_numeric_boundary_fixtures.py           # write
    python scripts/generate_numeric_boundary_fixtures.py --check   # verify
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FAMILY_DIR = (
    REPO_ROOT
    / "src"
    / "geocase"
    / "data"
    / "core"
    / "vector"
    / "special"
    / "precision"
)


@dataclass(frozen=True)
class BoundarySpec:
    """One coordinate property, isolated."""

    case_id: str
    title: str
    #: The single ``[x, y]`` the file carries.
    coordinate: tuple[float, float]
    #: What the point is *for*, in one line -- becomes the feature property and
    #: the case description's first clause.
    property_tested: str
    #: Why this magnitude or pattern and not a neighbouring one.
    rationale: str
    risk_types: tuple[str, ...]


SPECS: tuple[BoundarySpec, ...] = (
    BoundarySpec(
        case_id="numeric_boundary_15_significant_digits",
        title="Numeric Boundary: 15 Significant Digits",
        coordinate=(10.123456789012345, 50.987654321098765),
        property_tested="round-trips in exactly 15 significant digits",
        rationale=(
            "The control for the 17-digit case. GDAL's writers default to 15 "
            "decimal places, so this value is inside the default and must "
            "survive unchanged; a consumer that loses it has a precision "
            "problem unrelated to the boundary the family is about."
        ),
        risk_types=(
            "precision/significant_digits",
            "precision/formatter_boundary",
            "failure_mode/reference_implementation",
        ),
    ),
    BoundarySpec(
        case_id="numeric_boundary_17_significant_digits",
        title="Numeric Boundary: 17 Significant Digits",
        coordinate=(0.1234567890123456789, 51.0),
        property_tested="needs 17 significant digits to round-trip",
        rationale=(
            "17 digits is the number IEEE 754 doubles need in the worst case, "
            "and it is two more than the 15 the writer emits by default. The "
            "value is therefore expected to change on a text round-trip -- "
            "which is a documented limit, not a defect, and the case exists so "
            "a consumer can tell that limit apart from the 1e-14 class, which "
            "is a defect."
        ),
        risk_types=(
            "precision/significant_digits",
            "precision/roundtrip_degradation",
            "precision/formatter_boundary",
            "failure_mode/reference_implementation",
        ),
    ),
    BoundarySpec(
        case_id="numeric_boundary_trailing_zeros",
        title="Numeric Boundary: Trailing Zeros",
        coordinate=(0.000000010000001, 50.000000010000001),
        property_tested="decimal expansion at 15 places ends in zeros",
        rationale=(
            "One of the two patterns ``intelliround`` "
            "(ogr/ogrutils.cpp:161-169) special-cases: it tests s[len-3] "
            "through s[len-9] for zeros and then drops the last 8 characters, "
            "including the untested s[len-2]. 0.000000010000001 loses its "
            "trailing 1 through exactly this path, which is the same mechanism "
            "as the 1e-14 finding at a magnitude nobody would call small."
        ),
        risk_types=(
            "precision/formatter_boundary",
            "precision/loss",
            "failure_mode/reference_implementation",
        ),
    ),
    BoundarySpec(
        case_id="numeric_boundary_trailing_nines",
        title="Numeric Boundary: Trailing Nines",
        coordinate=(0.999999999999999, 50.999999999999999),
        property_tested="decimal expansion at 15 places ends in nines",
        rationale=(
            "The other pattern ``intelliround`` special-cases, and the one "
            "where rounding up carries across every digit. The y value is "
            "also the case where the carry crosses an integer boundary, so a "
            "consumer rounding to 15 places returns 51.0 for a point that was "
            "never at 51."
        ),
        risk_types=(
            "precision/formatter_boundary",
            "precision/loss",
            "failure_mode/reference_implementation",
        ),
    ),
    BoundarySpec(
        case_id="numeric_boundary_1e13",
        title="Numeric Boundary: 1e-13",
        coordinate=(1e-13, 1e-13),
        property_tested="one decade above the affected magnitude class",
        rationale=(
            "The upper bracket. A brute force over 300000 coordinates puts "
            "GDAL's zeroing class at exactly |v| in [1e-14, 1e-13), so this "
            "value must survive. A consumer that loses it has a wider bug than "
            "the one round 6 found."
        ),
        risk_types=(
            "precision/denormal_magnitude",
            "precision/formatter_boundary",
            "failure_mode/reference_implementation",
        ),
    ),
    BoundarySpec(
        case_id="numeric_boundary_1e14",
        title="Numeric Boundary: 1e-14",
        coordinate=(1e-14, 1e-14),
        property_tested="inside the affected magnitude class",
        rationale=(
            "The hit. GDAL d6fd56f52d writes this coordinate as 0 through both "
            "the WKT and the GeoJSON writers, silently, at relative error 1.0. "
            "Not a precision floor: 1e-14 is 0.00000000000001, fourteen "
            "decimal places, inside the writer's default of fifteen. This is "
            "the case precision_loss_geojson_roundtrip found by accident, "
            "isolated so that finding it again is not an accident."
        ),
        risk_types=(
            "precision/denormal_magnitude",
            "precision/formatter_boundary",
            "precision/loss",
            "failure_mode/reference_implementation",
        ),
    ),
    BoundarySpec(
        case_id="numeric_boundary_1e15",
        title="Numeric Boundary: 1e-15",
        coordinate=(1e-15, 1e-15),
        property_tested="one decade below the affected magnitude class",
        rationale=(
            "The lower bracket, and the one that separates 'GDAL's "
            "intelliround bug' from 'the value fell off the end of 15 decimal "
            "places'. 1e-15 is at the writer's declared limit, so losing it is "
            "documented behaviour; losing 1e-14 is not."
        ),
        risk_types=(
            "precision/denormal_magnitude",
            "precision/significant_digits",
            "precision/formatter_boundary",
            "failure_mode/reference_implementation",
        ),
    ),
)


def _geojson(spec: BoundarySpec) -> str:
    """Return the FeatureCollection text for *spec*.

    ``json.dumps`` emits ``repr``-shortest doubles, which is the round-trip
    exact form -- the file therefore carries the double the case is about, not
    a decimal approximation of it.
    """
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": 1,
                    "description": spec.property_tested,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [spec.coordinate[0], spec.coordinate[1]],
                },
            }
        ],
    }
    return json.dumps(doc, indent=2) + "\n"


def _case_yaml(spec: BoundarySpec) -> str:
    """Return the ``case.yaml`` text for *spec*.

    Deliberately emits **no** ``extent:`` block. ``scripts/catalog_extent.py``
    owns that field and writes it rounded to six decimal places from the real
    bytes; generating a competing value here would make the two gates
    contradict each other on every run. The exact coordinate lives in
    ``assertions.expected_roundtrip_coordinates``, which is the field that has
    to be exact.
    """
    x, y = spec.coordinate
    risks = "\n".join(f"  - {t}" for t in spec.risk_types)
    return f"""\
# Generated by scripts/generate_numeric_boundary_fixtures.py -- do not edit by
# hand. Plan 44 phase 2.
id: {spec.case_id}
title: "{spec.title}"
description: >
  A single-point GeoJSON whose coordinate {spec.property_tested}.
  {spec.rationale}
category: vector
format: GeoJSON
test_tier: unit
size_class: tiny
storage_class: bundled
redistributable: true
schema_version: "1.0"
status: validated

tags:
  - vector
  - geojson
  - precision
  - numeric_boundary
  - single_variable

risk_types:
{risks}

behavioral_goal: >
  Establish whether a text write/read cycle returns this coordinate unchanged.
  The expected answer ships with the case, so a consumer is graded rather than
  left to re-derive what "survived" means.

expected_capabilities:
  - load
  - geometry-validation
  - coordinate-precision-check

loader_hint: geopandas
geometry_type: Point
crs: EPSG:4326

files:
  primary: {spec.case_id}.geojson
  notes: notes.md

source:
  name: geocase-synthetic
  license: MIT

assertions:
  expect_loadable: true
  expect_valid_geometry: true
  expect_crs: true
  expected_epsg: 4326
  expected_geometry_types:
    - Point
  # Plan 44 phase 2.2 -- the answer, typed, so the gate and the consumer read
  # the same field.
  expected_roundtrip_coordinates:
    - [{x!r}, {y!r}]

params:
  generator: scripts/generate_numeric_boundary_fixtures.py
"""


def _notes(spec: BoundarySpec) -> str:
    x, y = spec.coordinate
    return f"""\
# {spec.title}

<!-- Generated by scripts/generate_numeric_boundary_fixtures.py. -->

## The property

The single point in this file {spec.property_tested}:

| | value | shortest round-trip repr |
|---|---|---|
| x | `{x!r}` | `{x!r}` |
| y | `{y!r}` | `{y!r}` |

One feature, one property. Plan 40's control principle: if a consumer fails
this case and passes its siblings, the failure names the property.

## Why this value

{spec.rationale}

## What to assert

`assertions.expected_roundtrip_coordinates` carries the pair the file holds.
Write the case out in your own format, read it back, and compare against that
field rather than against a tolerance you chose:

```python
import geocase

meta = geocase.get_case("{spec.case_id}")
expected = meta.assertions.expected_roundtrip_coordinates
```

A tolerance hides the failure this family exists to find -- GDAL
`d6fd56f52d` writes `1e-14` as `0`, and every tolerance loose enough to be
"reasonable" for a coordinate near zero passes that silently.

## Provenance

Plan 44 phase 2, from the 2026-09-06 run against GDAL `d6fd56f52d`. See
[docs/plans/44-gdal-as-target-and-the-numeric-axis.md](https://github.com/farzinashouri/geocase/blob/main/docs/plans/44-gdal-as-target-and-the-numeric-axis.md).
"""


def _targets(spec: BoundarySpec) -> dict[Path, str]:
    """Return the files this script owns **byte for byte**.

    ``case.yaml`` is not among them: ``scripts/catalog_extent.py`` writes an
    ``extent:`` block into it after generation, so a byte comparison here would
    fail on every run against the other gate's own correct output. It is
    seeded by :func:`_seed_case_yaml` and checked by
    :func:`_case_yaml_drift` on the fields this script actually decides.
    """
    case_dir = FAMILY_DIR / spec.case_id
    return {
        case_dir / f"{spec.case_id}.geojson": _geojson(spec),
        case_dir / "notes.md": _notes(spec),
    }


#: ``case.yaml`` fields this script decides, and which the corpus must not
#: drift away from. Everything else in the file (``extent:``) belongs to
#: another generator.
_OWNED_LINES = ("id: ", "category: ", "format: ", "loader_hint: ", "crs: ")


def _case_yaml_drift(spec: BoundarySpec) -> str | None:
    """Return a description of how *spec*'s ``case.yaml`` has drifted, or None."""
    path = FAMILY_DIR / spec.case_id / "case.yaml"
    if not path.exists():
        return "missing"

    actual = path.read_text()
    expected = _case_yaml(spec)

    for prefix in _OWNED_LINES:
        want = next(ln for ln in expected.splitlines() if ln.startswith(prefix))
        if want not in actual.splitlines():
            return f"{prefix.strip()} does not match the generator"

    for term in spec.risk_types:
        if f"  - {term}" not in actual:
            return f"risk type {term} is missing"

    x, y = spec.coordinate
    if f"    - [{x!r}, {y!r}]" not in actual:
        return "expected_roundtrip_coordinates does not match the generator"

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any generated file is missing or stale.",
    )
    args = parser.parse_args()

    stale: list[Path] = []
    for spec in SPECS:
        for path, content in _targets(spec).items():
            if args.check:
                if not path.exists() or path.read_text() != content:
                    stale.append(path)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

        case_yaml = FAMILY_DIR / spec.case_id / "case.yaml"
        if args.check:
            drift = _case_yaml_drift(spec)
            if drift is not None:
                stale.append(case_yaml)
                print(f"  {case_yaml.name} ({spec.case_id}): {drift}")
        elif not case_yaml.exists():
            # Seeded once; catalog_extent.py then adds the extent block it
            # owns, and re-running this script must not delete that.
            case_yaml.parent.mkdir(parents=True, exist_ok=True)
            case_yaml.write_text(_case_yaml(spec))

    if args.check:
        if stale:
            print("Stale or missing numeric-boundary fixtures:")
            for path in stale:
                print(f"  {path.relative_to(REPO_ROOT)}")
            print("Run: python scripts/generate_numeric_boundary_fixtures.py")
            return 1
        print(f"OK: {len(SPECS)} numeric-boundary cases up to date.")
        return 0

    print(f"Wrote {len(SPECS)} numeric-boundary cases under {FAMILY_DIR}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
