"""Differential testing — read every case two ways and compare the results.

Plan 28 phase 2.6. This is the shape of testing the external validation run
actually found productive::

    Both bugs here came from comparing a consumer against **itself**, not
    against geocase's assertions. The most productive thing built was ~100
    lines: read every case two ways, compare, report divergences.

    -- docs/geocase_validate/geocase-improvement-report.md

The pattern generalises to any library with two code paths that should agree:
numpy vs Arrow, eager vs lazy, C vs pure Python, an old version vs a new one.
Neither path is the oracle. The finding is the *disagreement*, which is why
this mode works on libraries whose correct answer geocase does not know — and
why it found bugs where assert-against-declared-truth found none.

Usage::

    from functools import partial

    import pyogrio

    import geocase
    from geocase.differential import compare_cases, summarize

    results = compare_cases(
        left=partial(pyogrio.read_dataframe, use_arrow=False),
        right=partial(pyogrio.read_dataframe, use_arrow=True),
        consumer="pyogrio",
        category="vector",
    )

    print(summarize(results))
    for result in results:
        if result.outcome == "diverged":
            print(result.case_id, result.detail)

Divergences already investigated are recorded per case in
:attr:`~geocase.catalog.models.CaseMetadata.known_divergences` and reported as
``known`` rather than ``diverged``, so a repeat run surfaces only what is new.
Pass ``consumer=`` to opt into that: a record only excuses the consumer it was
recorded against, or one catalogued quirk would silence every future finding on
the same case.

Deliberately **not** in ``geocase.__all__``: it is a submodule import, the same
precedent :mod:`geocase.raster` and :mod:`geocase.assertions` set. Scoped to
the vector / two-code-path shape the evidence covers; the raster adapter
protocol is Phase 4 and is not started.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from geocase.catalog.models import CaseMetadata, KnownDivergence

__all__ = [
    "DifferentialResult",
    "Outcome",
    "compare_case",
    "compare_cases",
    "default_compare",
    "summarize",
]

#: What a single two-path comparison concluded.
#:
#: * ``agree`` -- both paths produced the same result, *or* both raised the
#:   same way. A curated-failure case is agreement: the two paths agree that it
#:   fails. Calling that a divergence would report a finding on every expected
#:   failure in the corpus and bury the real ones.
#: * ``diverged`` -- the finding. The two paths disagree, and nothing on the
#:   case says they were expected to.
#: * ``known`` -- they disagree, and :attr:`CaseMetadata.known_divergences`
#:   already records it for this consumer. Not a finding; not silence either,
#:   because the record is attached to the result.
#: * ``errored`` -- exactly one path raised. Distinct from ``diverged``
#:   because a crash and a wrong answer need different triage, and distinct
#:   from ``agree`` because a one-sided crash is never fine.
Outcome = Literal["agree", "diverged", "known", "errored"]

#: A reader: given the path to a case's primary file, return whatever it reads.
Reader = Callable[[Path], Any]


@dataclass(frozen=True)
class DifferentialResult:
    """One case, read two ways.

    Attributes:
        case_id: The case compared.
        outcome: See :data:`Outcome`.
        detail: What differed, or the exception text, in a line a human reads.
            ``None`` only when the outcome is ``agree``.
        known_divergence: The catalogued record that made this ``known``.
        left: The left path's result, kept so a caller can inspect the actual
            objects rather than only the message. ``None`` if that path raised.
        right: The right path's result, same.
    """

    case_id: str
    outcome: Outcome
    detail: str | None = None
    known_divergence: KnownDivergence | None = None
    left: Any = None
    right: Any = None


def _describe(value: Any) -> str:
    """A short, comparable description of whatever a reader returned."""
    columns = getattr(value, "columns", None)
    if columns is not None and hasattr(value, "__len__"):
        return f"{type(value).__name__}({len(value)} rows, columns={list(columns)})"
    if hasattr(value, "__len__") and not isinstance(value, str | bytes):
        return f"{type(value).__name__}(len={len(value)})"
    return f"{type(value).__name__}({value!r})"


#: Returned by :func:`_frames_differ` when the inputs are not dataframes at all.
#:
#: Distinct from ``None``, which means "they *are* frames and they agree".
#: Conflating the two would send an equal pair of GeoDataFrames on to the
#: scalar path, where ``a != a`` raises on a frame.
_NOT_FRAMES = object()


def _frames_differ(left: Any, right: Any) -> str | None | object:
    """Compare two dataframe-shaped results.

    Returns a description of the difference, ``None`` if they are frames that
    agree, or :data:`_NOT_FRAMES` if neither is a frame.

    Frames need their own path because ``left == right`` on a DataFrame is
    *elementwise* and returns a frame, whose truthiness raises. Shape and
    columns are checked before contents so the reported difference is the one
    a reader can act on: "2 rows against 3" is the whole GPKG finding.
    """
    if not (hasattr(left, "columns") and hasattr(right, "columns")):
        return _NOT_FRAMES

    if len(left) != len(right):
        return f"row count differs: {len(left)} vs {len(right)}"

    left_columns = list(left.columns)
    right_columns = list(right.columns)
    if left_columns != right_columns:
        only_left = [c for c in left_columns if c not in right_columns]
        only_right = [c for c in right_columns if c not in left_columns]
        return (
            f"columns differ: left {left_columns} vs right {right_columns}"
            f" (left-only {only_left}, right-only {only_right})"
        )

    for column in left_columns:
        left_values = list(left[column])
        right_values = list(right[column])
        for row, (a, b) in enumerate(zip(left_values, right_values, strict=True)):
            if not _values_equal(a, b):
                return f"column {column!r} differs at row {row}: {a!r} vs {b!r}"
    return None


def _is_nan(value: Any) -> bool:
    """True only for a scalar NaN, never for something array-shaped.

    ``value != value`` is the NaN idiom, but it is *elementwise* on anything
    array-shaped and its truthiness then raises, so the isinstance guard is
    load-bearing rather than defensive.
    """
    return isinstance(value, float) and value != value  # noqa: PLR0124


def _is_missing(value: Any) -> bool:
    """True for any of the several things two readers spell "absent".

    ``None``, float ``NaN``, ``pandas.NaT`` and ``pandas.NA`` all mean the same
    thing and no two readers agree on which to return. The external pyogrio run
    predicted exactly this and called it "the kind of noise a differential
    harness has to be taught to ignore" — on this corpus it is 7 KML cases
    reporting ``None`` on the numpy path against ``nan`` on the Arrow path.
    Reporting those as findings buries the one real divergence among them.

    Deliberately *not* extended to ``""`` or ``0``: those are values a reader
    genuinely returned, and a harness that equates them to absence would hide a
    real defect. If you need missing-vs-missing to be visible, pass your own
    ``compare=``.
    """
    if value is None or _is_nan(value):
        return True
    # NaT and NA are pandas singletons with no public isinstance target that
    # covers both, and pandas is an optional dependency here.
    return type(value).__name__ in {"NaTType", "NAType"}


def _values_equal(a: Any, b: Any) -> bool:
    """Elementwise equality that tolerates missing values and geometries."""
    a_missing, b_missing = _is_missing(a), _is_missing(b)
    if a_missing or b_missing:
        return a_missing and b_missing
    try:
        result = a == b
    except Exception:  # a reader may return something with no useful __eq__
        return repr(a) == repr(b)
    if isinstance(result, bool):
        return result
    return bool(getattr(result, "all", lambda: result)())


def default_compare(left: Any, right: Any) -> str | None:
    """Return a description of how two results differ, or ``None`` if equal.

    Handles the shapes the evidenced use actually produces — GeoDataFrames
    first, then anything with a working ``__eq__``. Pass your own ``compare=``
    when a difference is expected noise: the KML cases, for instance, produce
    ``object`` dtype on pyogrio's numpy path and pandas ``str`` on its Arrow
    path, which a real run has to be taught to ignore.
    """
    frame_difference = _frames_differ(left, right)
    if frame_difference is not _NOT_FRAMES:
        return frame_difference  # type: ignore[return-value]

    if _values_equal(left, right):
        return None
    return f"results differ: {_describe(left)} vs {_describe(right)}"


def _match_known(
    metadata: CaseMetadata, consumer: str | None
) -> KnownDivergence | None:
    """The catalogued record excusing this divergence, if there is one.

    Matching is on the consumer name alone. Matching on the *description* would
    require the harness to reproduce prose, and matching on nothing at all would
    let one catalogued quirk silence every future finding on the case.
    """
    if consumer is None:
        return None
    for divergence in metadata.known_divergences:
        if divergence.consumer == consumer:
            return divergence
    return None


def _read(reader: Reader, path: Path) -> tuple[Any, BaseException | None]:
    try:
        return reader(path), None
    except Exception as exc:  # a consumer crash is a result, not a stop
        return None, exc


def _same_failure(left: BaseException, right: BaseException) -> bool:
    """Two paths failing identically is agreement about the failure."""
    return type(left) is type(right) and str(left) == str(right)


def compare_case(
    case_dir: Path | str,
    metadata: CaseMetadata,
    *,
    left: Reader,
    right: Reader,
    compare: Callable[[Any, Any], str | None] = default_compare,
    consumer: str | None = None,
) -> DifferentialResult:
    """Read one case both ways and classify what came back.

    Args:
        case_dir: Directory holding the case's ``case.yaml`` and payload.
        metadata: The case being compared.
        left: One reader, called with the primary file's path.
        right: The other reader, called the same way.
        compare: Returns a description of how two results differ, or ``None``
            when they agree. Defaults to :func:`default_compare`.
        consumer: The library under test, e.g. ``"pyogrio"``. Required for a
            catalogued divergence to be honoured; without it every divergence
            is reported as new.

    Returns:
        One :class:`DifferentialResult`. Never raises for a reader failure —
        a crash is a finding, and stopping on the first one is what makes a
        harness useless over a corpus.
    """
    path = Path(case_dir) / metadata.files.primary

    left_value, left_error = _read(left, path)
    right_value, right_error = _read(right, path)

    if left_error is not None and right_error is not None:
        if _same_failure(left_error, right_error):
            return DifferentialResult(metadata.id, "agree")
        return _classify_divergence(
            metadata,
            consumer,
            detail=(
                f"both paths failed, differently: "
                f"{type(left_error).__name__}: {left_error} "
                f"vs {type(right_error).__name__}: {right_error}"
            ),
        )

    if left_error is not None or right_error is not None:
        side = "left" if left_error is not None else "right"
        error = left_error or right_error
        return DifferentialResult(
            metadata.id,
            "errored",
            detail=f"{side} path raised {type(error).__name__}: {error}",
            left=left_value,
            right=right_value,
        )

    difference = compare(left_value, right_value)
    if difference is None:
        return DifferentialResult(
            metadata.id, "agree", left=left_value, right=right_value
        )

    return _classify_divergence(
        metadata, consumer, detail=difference, left=left_value, right=right_value
    )


def _classify_divergence(
    metadata: CaseMetadata,
    consumer: str | None,
    *,
    detail: str,
    left: Any = None,
    right: Any = None,
) -> DifferentialResult:
    """A real disagreement: new, or one this case already documents."""
    known = _match_known(metadata, consumer)
    if known is not None:
        return DifferentialResult(
            metadata.id,
            "known",
            detail=detail,
            known_divergence=known,
            left=left,
            right=right,
        )
    return DifferentialResult(
        metadata.id, "diverged", detail=detail, left=left, right=right
    )


def compare_cases(
    *,
    left: Reader,
    right: Reader,
    compare: Callable[[Any, Any], str | None] = default_compare,
    consumer: str | None = None,
    cases: Iterable[CaseMetadata] | None = None,
    **selection: Any,
) -> list[DifferentialResult]:
    """Read every selected case both ways.

    Args:
        left: One reader, called with each case's primary file path.
        right: The other reader.
        compare: See :func:`compare_case`.
        consumer: See :func:`compare_case`.
        cases: Compare exactly these, bypassing selection. Use this for cases
            from an external manifest, or to re-run a shortlist.
        **selection: Forwarded verbatim to :func:`geocase.list_cases`, so the
            catalog's own selectors are reused rather than reinvented —
            ``category="vector"``, ``risk_types_any=[...]``, ``include_ids``,
            and the rest.

    Returns:
        One :class:`DifferentialResult` per case, in catalog order.
    """
    import geocase
    from geocase.catalog.roots import case_roots_by_id

    selected = list(cases) if cases is not None else geocase.list_cases(**selection)
    roots = case_roots_by_id()

    results: list[DifferentialResult] = []
    for metadata in selected:
        case_dir = roots.get(metadata.id)
        if case_dir is None:
            # A manifest case whose data was never fetched. Reporting it as a
            # finding would blame the consumer for geocase's missing bytes.
            results.append(
                DifferentialResult(
                    metadata.id,
                    "errored",
                    detail="case data is not materialized on this machine",
                )
            )
            continue
        results.append(
            compare_case(
                case_dir,
                metadata,
                left=left,
                right=right,
                compare=compare,
                consumer=consumer,
            )
        )
    return results


def summarize(results: Iterable[DifferentialResult]) -> dict[str, int]:
    """Count results by outcome, with every outcome present even at zero.

    A key that disappears when its count is zero makes a report that has to be
    read differently depending on what it found, which is how a run with one
    new divergence gets skimmed as if it were clean.
    """
    counts: dict[str, int] = {
        "agree": 0,
        "diverged": 0,
        "known": 0,
        "errored": 0,
    }
    for result in results:
        counts[result.outcome] += 1
    return counts
