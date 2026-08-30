"""Differential testing: read every case two ways and compare — plan 28 §2.6.

This is the mode with external evidence behind it. An independent validation
run against pyogrio found two real defects (a `read_dataframe` crash, since
patched upstream, and a GPKG spatial-filter divergence traced into GDAL's
`GetArrowStream`) — and **both came from comparing pyogrio against itself**,
not from any assertion geocase declares. Neither path is the oracle here; the
finding is the disagreement.

The pattern generalises to any library with two code paths that ought to agree:
numpy vs Arrow, eager vs lazy, C vs pure Python, an old release vs a new one.
Swap the two readers below for your own and the rest carries over unchanged.

Run it::

    pytest examples/test_differential_pyogrio.py -q -s
"""

from __future__ import annotations

from functools import partial

import pytest

import geocase
from geocase.differential import compare_cases, summarize

pyogrio = pytest.importorskip("pyogrio")
pytest.importorskip("pyarrow")  # pyogrio's Arrow path needs it


# The bbox from the upstream GDAL report: it covers both valid points in
# `empty_geometry_gpkg`, and excludes the NULL-geometry row -- a NULL geometry
# intersects nothing. The divergence only appears *under a spatial filter*.
_BBOX = (9.9, 49.9, 11.1, 51.1)


def _openable_vector_cases() -> list[geocase.CaseMetadata]:
    """The vector cases this pyogrio build can actually open.

    Without this filter, 20 of the 113 vector cases report as `errored` for a
    reason that is not the consumer's fault: 13 are bare WKB/WKT geometry blobs
    that no OGR driver opens at all, and 7 need `libgdal-arrow-parquet`.
    `required_drivers` is what makes that predictable *before* reading, which
    is the whole point of the field.
    """
    available = set(pyogrio.list_drivers())
    return [
        case
        for case in geocase.list_cases(category="vector")
        if all(driver in available for driver in case.assertions.required_drivers)
    ]


def test_numpy_and_arrow_paths_agree_on_the_unfiltered_corpus() -> None:
    """Read every openable vector case both ways, with no filter.

    A clean run is the expected result and is not a wasted one: it is the
    baseline that makes the *next* run's single divergence legible.
    """
    results = compare_cases(
        left=partial(pyogrio.read_dataframe, use_arrow=False),
        right=partial(pyogrio.read_dataframe, use_arrow=True),
        consumer="pyogrio",
        cases=_openable_vector_cases(),
    )

    print(f"\nunfiltered: {summarize(results)}")
    for result in results:
        if result.outcome in {"diverged", "errored"}:
            print(f"  {result.outcome:9} {result.case_id}: {result.detail}")

    assert results, "expected pyogrio to open at least some vector cases"


def test_the_catalogued_gpkg_divergence_reports_as_known() -> None:
    """The 2.5 half: a finding investigated once stays investigated.

    Under a spatial filter, pyogrio's Arrow path returns the NULL-geometry row
    that its numpy path and GDAL's own `ogrinfo -spat` both exclude. That is
    recorded in `empty_geometry_gpkg`'s `known_divergences`, so a repeat run
    reports it as `known` rather than sending the next person to investigate
    a GDAL bug that is already filed.
    """
    read = partial(pyogrio.read_dataframe, bbox=_BBOX)
    results = compare_cases(
        left=partial(read, use_arrow=False),
        right=partial(read, use_arrow=True),
        consumer="pyogrio",
        include_ids=["empty_geometry_gpkg"],
    )
    (result,) = results

    print(f"\nfiltered: {result.outcome} -- {result.detail}")

    # `known` on a GDAL that still has the bug, `agree` once it is fixed. Both
    # are acceptable outcomes for an example that runs on any GDAL build; what
    # must never happen is `diverged`, which would mean the record failed to
    # match the finding it was written for.
    assert result.outcome in {"known", "agree"}
    if result.outcome == "known":
        assert result.known_divergence is not None
        assert result.known_divergence.consumer == "pyogrio"
        assert result.known_divergence.upstream_url


def test_without_a_consumer_the_same_divergence_is_reported_as_new() -> None:
    """A record only excuses the consumer it was recorded against.

    Omitting `consumer=` opts out of the catalogue entirely, which is what you
    want when auditing whether the recorded divergences are still real.
    """
    read = partial(pyogrio.read_dataframe, bbox=_BBOX)
    (result,) = compare_cases(
        left=partial(read, use_arrow=False),
        right=partial(read, use_arrow=True),
        include_ids=["empty_geometry_gpkg"],
    )

    assert result.outcome in {"diverged", "agree"}
