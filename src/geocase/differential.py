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

The same shape works on rasters, using :func:`compare_arrays` in place of
:func:`default_compare`. A raster reader is already a :data:`Reader` — a
callable taking the primary file's path — so nothing else changes::

    from rio_tiler.io import Reader

    from geocase.differential import compare_arrays, compare_cases

    def read_native(path):
        with Reader(path) as src:
            return src.read().data

    def read_part(path):
        with Reader(path) as src:
            return src.part(src.geographic_bounds).data

    results = compare_cases(
        left=read_native,
        right=read_part,
        compare=compare_arrays,
        consumer="rio-tiler",
        category="raster",
    )

That pair is not an illustration: it is what found rio-tiler's rotated-affine
defect on ``rotated_two_islands``, where ``read()`` returned 9 valid pixels and
``part()`` 4 against a ``WarpedVRT`` reference of 7, silently. Compare masks in
their own call — values and masks are separate findings, and that case diverged
on both.

Deliberately **not** in ``geocase.__all__``: it is a submodule import, the same
precedent :mod:`geocase.raster` and :mod:`geocase.assertions` set.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from geocase.catalog.models import CaseMetadata, KnownDivergence

__all__ = [
    "DEFAULT_MAX_PIXELS",
    "OPTION_PAIRS",
    "PROBE_EXPLANATIONS",
    "DifferentialResult",
    "OptionPair",
    "Outcome",
    "PixelBudgetError",
    "ProbeExplanation",
    "ReaderTimeoutError",
    "compare_arrays",
    "compare_case",
    "compare_cases",
    "compare_geometries",
    "crs_equal",
    "default_compare",
    "explain_divergence",
    "guarded_reader",
    "option_pairs",
    "summarize",
    "to_common_currency",
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
        probe_explanation: The shipped :class:`ProbeExplanation` that made
            this ``known``, when the divergence was classified by
            :func:`explain_divergence` rather than by a catalogued record.
    """

    case_id: str
    outcome: Outcome
    detail: str | None = None
    known_divergence: KnownDivergence | None = None
    left: Any = None
    right: Any = None
    probe_explanation: ProbeExplanation | None = None


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

    # Plan 38 Phase 3.2. A CRS-shaped mapping is compared with :func:`crs_equal`
    # rather than by ``==``, because ``OGC:CRS84`` and ``EPSG:4326`` are the
    # same CRS and calling them different produced five false findings.
    crs_difference = _crs_mappings_differ(left, right)
    if crs_difference is not _NOT_CRS:
        return crs_difference  # type: ignore[return-value]

    if _values_equal(left, right):
        return None
    return f"results differ: {_describe(left)} vs {_describe(right)}"


#: Returned by :func:`_crs_mappings_differ` when the inputs are not CRS-shaped.
_NOT_CRS = object()

#: Keys a mapping uses to spell "this is the CRS".
_CRS_KEYS = ("crs", "crs_wkt", "srs", "proj:code", "proj:epsg")


def _crs_mappings_differ(left: Any, right: Any) -> str | None | object:
    """Compare two mappings that carry a CRS, using :func:`crs_equal` for it."""
    if not (isinstance(left, dict) and isinstance(right, dict)):
        return _NOT_CRS
    crs_keys = [key for key in _CRS_KEYS if key in left and key in right]
    if not crs_keys or set(left) != set(right):
        return _NOT_CRS

    for key in sorted(left):
        if key in crs_keys:
            if not crs_equal(left[key], right[key]):
                return f"CRS at {key!r} differs: {left[key]!r} vs {right[key]!r}"
        elif not _values_equal(left[key], right[key]):
            return f"{key!r} differs: {left[key]!r} vs {right[key]!r}"
    return None


def compare_arrays(left: Any, right: Any) -> str | None:
    """Compare two array-shaped results, or ``None`` if they agree.

    The raster counterpart to :func:`default_compare`, with the same
    ``str | None`` contract, so it drops straight into ``compare=`` on
    :func:`compare_case` and :func:`compare_cases` with no other change::

        from functools import partial

        from rio_tiler.io import Reader

        from geocase.differential import compare_arrays, compare_cases

        def read_native(path):
            with Reader(path) as src:
                return src.read().data

        def read_part(path):
            with Reader(path) as src:
                return src.part(src.geographic_bounds).data

        results = compare_cases(
            left=read_native,
            right=read_part,
            compare=compare_arrays,
            consumer="rio-tiler",
            category="raster",
        )

    That exact pair found the rotated-affine defect on ``rotated_two_islands``:
    ``read()`` returned 9 valid pixels and ``part()`` 4, against a ``WarpedVRT``
    reference of 7, with no error and no warning from either path.

    Three behaviours are load-bearing, each because the hand-written harness
    that found the defects got it wrong first:

    * **Shape is checked before contents.** A cell-by-cell report on arrays of
      different shape is unreadable, and the shapes are the whole finding.
    * **NaN compares equal to NaN in the same position.** ``np.array_equal``
      calls every NaN-nodata raster diverged; two of that run's three initial
      findings were this and nothing else. A NaN against a number, or a NaN
      that *moved*, is still a divergence.
    * **Comparison is by equality, never truthiness.** A mask of 255 against a
      mask of 1 is a real difference — it is rio-tiler's ``ImageData.mask``
      contract defect — and the harness's ``mask > 0`` stepped over it because
      truthiness is correct at every dtype.

    Values and masks are separate findings and should be compared separately;
    ``rotated_two_islands`` diverged on both, and a comparator handed only the
    values reports half the defect. Pass the mask arrays in their own
    :func:`compare_cases` call, or read with ``masked=True`` — a masked array's
    mask is compared here as part of the value, and data under the mask is
    ignored, which is what makes two different fill values agree.

    Args:
        left: One array-shaped result. Anything ``numpy.asanyarray`` accepts,
            including a nested sequence or a masked array.
        right: The other.

    Returns:
        A description of the first difference, or ``None`` if they agree.

    Raises:
        ImportError: If numpy is not installed. Raster comparison is
            array comparison; there is no meaningful fallback.
    """
    import numpy as np

    left_array = np.asanyarray(left)
    right_array = np.asanyarray(right)

    if left_array.shape != right_array.shape:
        return f"shape differs: {left_array.shape} vs {right_array.shape}"

    left_mask = np.ma.getmaskarray(left_array)
    right_mask = np.ma.getmaskarray(right_array)
    if not np.array_equal(left_mask, right_mask):
        differing = int(np.count_nonzero(left_mask != right_mask))
        index = tuple(int(i) for i in np.argwhere(left_mask != right_mask)[0])
        return (
            f"mask differs in {differing} cell(s); first at {index}: "
            f"{bool(left_mask[index])} vs {bool(right_mask[index])}"
        )

    left_values = np.ma.getdata(left_array)
    right_values = np.ma.getdata(right_array)

    # Equality, not truthiness: a 255 mask against a 1 mask is a real finding.
    # NaN never equals itself, so tolerate it only where *both* sides are NaN —
    # a NaN that moved is still a divergence.
    unequal = left_values != right_values
    both_nan = _nan_positions(left_values) & _nan_positions(right_values)
    unequal = unequal & ~both_nan & ~left_mask

    if not unequal.any():
        return None

    differing = int(np.count_nonzero(unequal))
    index = tuple(int(i) for i in np.argwhere(unequal)[0])
    return (
        f"values differ in {differing} cell(s); first at {index}: "
        f"{left_values[index]!r} vs {right_values[index]!r}"
    )


def _nan_positions(array: Any) -> Any:
    """A boolean array marking NaN cells, ``False`` everywhere at integer dtype.

    ``np.isnan`` raises a ``TypeError`` on integer and object arrays rather
    than returning all-``False``, and a raster corpus carries plenty of both.
    """
    import numpy as np

    if array.dtype.kind in "fc":
        return np.isnan(array)
    return np.zeros(array.shape, dtype=bool)


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
    explain: bool = False,
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
        explain: Classify divergences against :data:`PROBE_EXPLANATIONS`,
            reporting a matched one as ``known`` with its
            :class:`ProbeExplanation` attached. Off by default: a caller who
            did not ask should see the raw divergence, because an explanation
            that fires unasked is indistinguishable from a comparator bug.

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
            explain=explain,
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
        metadata,
        consumer,
        detail=difference,
        left=left_value,
        right=right_value,
        explain=explain,
    )


def _classify_divergence(
    metadata: CaseMetadata,
    consumer: str | None,
    *,
    detail: str,
    left: Any = None,
    right: Any = None,
    explain: bool = False,
) -> DifferentialResult:
    """A real disagreement: new, or one already explained.

    Two kinds of "already explained" exist and they are kept distinct.
    :attr:`CaseMetadata.known_divergences` excuses a divergence on *this case*
    against *this consumer*; a :class:`ProbeExplanation` excuses a whole
    *class* of disagreement wherever it appears (Plan 38 Phase 3.3). The
    catalogued record wins when both apply, because it is the more specific
    statement.
    """
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
    if explain:
        explanation = explain_divergence(detail, left=left, right=right)
        if explanation is not None:
            return DifferentialResult(
                metadata.id,
                "known",
                detail=detail,
                left=left,
                right=right,
                probe_explanation=explanation,
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
    explain: bool = False,
    cases: Iterable[CaseMetadata] | None = None,
    **selection: Any,
) -> list[DifferentialResult]:
    """Read every selected case both ways.

    Args:
        left: One reader, called with each case's primary file path.
        right: The other reader.
        compare: See :func:`compare_case`.
        consumer: See :func:`compare_case`.
        explain: See :func:`compare_case`.
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
                explain=explain,
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


# ---------------------------------------------------------------------------
# Plan 38 Phase 2.2 -- guardrails, because a differential harness can hang or OOM
# ---------------------------------------------------------------------------

#: Pixel cap a guarded reader allows before refusing to compute.
#:
#: Round 2's first sweep was killed by the OS after 28 CPU-minutes and 3 GB RSS
#: because odc-stac derived a 3.17e12 pixel grid from an antimeridian source.
#: That derivation *is* the finding, and a harness that dies while allocating
#: it reports nothing at all. 512 megapixels is far above anything the corpus
#: contains and far below anything a laptop survives materializing at float64.
DEFAULT_MAX_PIXELS = 512 * 1024 * 1024


class PixelBudgetError(RuntimeError):
    """A reader was about to materialize an absurd derived grid.

    Raised *before* the read, from the size probe, so the grid is recorded as
    the finding rather than allocated. :func:`compare_case` turns it into an
    ``errored`` result like any other reader exception, which is the point:
    the run continues and the number appears in the report.
    """


class ReaderTimeoutError(RuntimeError):
    """A reader did not return inside its budget.

    Separate from :class:`PixelBudgetError` because the failures are
    upstream of each other: odc-stac's hang happens while *deriving* the
    geobox, before any shape a size check could see.
    """


def guarded_reader(
    reader: Reader,
    *,
    size_probe: Callable[[Any], tuple[int, ...]] | None = None,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    timeout: float | None = None,
) -> Reader:
    """Wrap *reader* so an absurd grid or a hang becomes a reported finding.

    Both guards are about fifteen lines and neither is discoverable until it
    has cost an afternoon::

        from geocase.differential import compare_cases, guarded_reader

        results = compare_cases(
            left=guarded_reader(read_odc, size_probe=probe_geobox, timeout=90),
            right=guarded_reader(read_stackstac, timeout=90),
            compare=compare_arrays,
            consumer="odc-stac",
            category="raster",
        )

    Args:
        reader: The reader to guard.
        size_probe: Called with the path *before* ``reader``; returns the shape
            the read would produce. Lazy by contract -- it must not compute the
            array. Omit it when the consumer offers no cheap way to ask.
        max_pixels: Refuse any probed shape whose product exceeds this.
        timeout: Seconds to allow the read. ``None`` disables the timeout.

    Returns:
        A :data:`Reader` with the same signature.
    """
    import math

    def guarded(path: Any) -> Any:
        if size_probe is not None:
            shape = tuple(int(value) for value in size_probe(path))
            pixels = math.prod(shape) if shape else 0
            if pixels > max_pixels:
                raise PixelBudgetError(
                    f"derived grid of {pixels} pixels {shape} exceeds the "
                    f"{max_pixels} pixel budget; not computed"
                )
        if timeout is None:
            return reader(path)
        return _call_with_timeout(reader, path, timeout)

    return guarded


def _call_with_timeout(reader: Reader, path: Any, timeout: float) -> Any:
    """Run *reader* in a worker thread, raising :class:`ReaderTimeoutError` if slow.

    A thread cannot be killed, so a hung consumer leaks one for the life of
    the process. That is deliberate and is the lesser evil: the alternative is
    a process pool, which cannot carry an open dataset handle across the
    boundary, and the alternative to *that* is the run dying at case 40 of 154.
    """
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as FutureTimeout

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(reader, path)
    try:
        return future.result(timeout=timeout)
    except FutureTimeout as exc:
        raise ReaderTimeoutError(
            f"reader did not return within {timeout}s on {path}"
        ) from exc
    finally:
        # Never block on a hung worker: shutdown(wait=True) would reintroduce
        # exactly the hang the timeout exists to escape.
        executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Plan 38 Phase 2.3 -- comparison in the common currency
# ---------------------------------------------------------------------------


def to_common_currency(array: Any, *, nodata: float | int | None = None) -> Any:
    """Return *array* as float64 with nodata folded to NaN.

    Cross-library raster comparison needs values in one representation, and
    round 2 settled on this one: float64, NaN for absent. It pairs with
    :func:`compare_arrays`, whose NaN-equals-NaN rule is what makes two
    readers' different fill values agree instead of producing a finding per
    nodata pixel.

    Note the trap it exists to absorb: ``.filled(np.nan)`` on an **integer**
    masked array raises, so the cast to float64 must precede the fill. That
    belongs here rather than in each consumer's harness.

    Args:
        array: Anything ``numpy.asanyarray`` accepts, including a masked array.
        nodata: A sentinel to fold to NaN in addition to any mask. A NaN
            passed here is a no-op, so the caller can forward a dataset's
            declared nodata without special-casing the NaN convention.

    Returns:
        A plain ``numpy.ndarray`` of dtype float64.

    Raises:
        ImportError: If numpy is not installed.
    """
    import numpy as np

    values = np.asanyarray(array)
    mask = np.ma.getmaskarray(values)
    # Cast first. This ordering is the whole point of the function.
    result = np.ma.getdata(values).astype(np.float64)

    if nodata is not None and not _is_nan(float(nodata)):
        result[result == float(nodata)] = np.nan
    if mask.any():
        result[mask] = np.nan
    return result


# ---------------------------------------------------------------------------
# Plan 38 Phase 3.1 -- the option-pair matrix, as data rather than prose
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OptionPair:
    """Two option sets a consumer should agree across, and why.

    Attributes:
        name: The axis, e.g. ``"explicit_crs"``.
        description: What varying this axis is meant to expose.
        left: One set of consumer options.
        right: The other. Always differs from ``left``.
        found_defect: Whether this axis has actually found a defect. Three
            have; the honest record of which is what makes a short sweep
            possible.
        evidence: Which finding, when ``found_defect``.
    """

    name: str
    description: str
    left: dict[str, Any]
    right: dict[str, Any]
    found_defect: bool = False
    evidence: str = ""


#: The eight axes round 2 varied, shipped as data.
#:
#: Round 2 is the evidence for what these are worth: **odc-stac's HIGH defect
#: needed ``crs=``**, **stackstac's needed ``dtype=``**, and odc-stac's
#: scale/offset defect needed a scaled case *and* a second library. A sweep
#: varying only library-against-library on a plain read -- Plan 37's recorded
#: failure -- finds none of the three.
#:
#: The option *keys* follow odc-stac / stackstac spelling. A consumer with
#: different names should map them rather than reinvent the matrix; the value
#: here is the enumeration of axes, not the keyword strings.
OPTION_PAIRS: tuple[OptionPair, ...] = (
    OptionPair(
        name="default",
        description=(
            "Both sides read with no options at all. The control: a "
            "divergence here is in the read itself, not in an option."
        ),
        left={},
        right={"_reader": "alternate"},
    ),
    OptionPair(
        name="explicit_crs",
        description=(
            "Reproject to a named CRS, including one that changes the "
            "linear unit. The unit-changing target is a single option value, "
            "it found a HIGH defect, and it is the one a consumer author is "
            "least likely to think of testing."
        ),
        left={"crs": "EPSG:32633"},
        right={"crs": "EPSG:4326"},
        found_defect=True,
        evidence="odc-stac HIGH: wrong grid when crs= changes the linear unit",
    ),
    OptionPair(
        name="resolution",
        description=(
            "Explicit resolution above and below native (10 m), so both "
            "upsampling and downsampling paths are exercised."
        ),
        left={"resolution": 5.0},
        right={"resolution": 30.0},
    ),
    OptionPair(
        name="bounds",
        description=(
            "Explicit bounds against the native footprint, which is where a "
            "window/offset error becomes visible."
        ),
        left={},
        right={"bbox": "native_shrunk_10pct"},
    ),
    OptionPair(
        name="nodata",
        description=(
            "Override the fill value against honouring the file's declared "
            "nodata. Compare in the common currency or every nodata pixel is "
            "a finding."
        ),
        left={},
        right={"nodata": -9999},
    ),
    OptionPair(
        name="dtype",
        description=(
            "Explicit output dtype against the native one. Found stackstac's "
            "defect, and does so on rasters whose values are otherwise equal."
        ),
        left={},
        right={"dtype": "float32"},
        found_defect=True,
        evidence="stackstac: dtype= changes values, not only representation",
    ),
    OptionPair(
        name="resampling",
        description=(
            "Nearest against bilinear. Only comparable where the two should "
            "agree -- constant-valued regions -- which is why the overlap "
            "cases carry distinct constant values."
        ),
        left={"resampling": "nearest"},
        right={"resampling": "bilinear"},
    ),
    OptionPair(
        name="chunking",
        description=(
            "Chunked against single-chunk. A chunk-boundary error is invisible "
            "at one chunk and is the classic lazy-against-eager divergence."
        ),
        left={"chunks": -1},
        right={"chunks": 4},
    ),
)


def option_pairs(
    *, axis: str | None = None, found_defect: bool | None = None
) -> list[OptionPair]:
    """Select from :data:`OPTION_PAIRS`.

    Args:
        axis: Return only the pairs on this axis.
        found_defect: Return only pairs whose ``found_defect`` matches. Pass
            ``True`` for the short sweep: the axes that have actually paid.

    Returns:
        The matching pairs, in matrix order.

    Raises:
        ValueError: If *axis* names no shipped axis -- a typo must not yield
            an empty sweep that reads as a clean run.
    """
    selected = list(OPTION_PAIRS)
    if axis is not None:
        selected = [pair for pair in selected if pair.name == axis]
        if not selected:
            names = sorted(pair.name for pair in OPTION_PAIRS)
            raise ValueError(f"unknown axis {axis!r}; expected one of {names}")
    if found_defect is not None:
        selected = [pair for pair in selected if pair.found_defect is found_defect]
    return selected


# ---------------------------------------------------------------------------
# Plan 38 Phase 3.2 -- an equality predicate that knows what a CRS is
# ---------------------------------------------------------------------------

#: CRS spellings that name the same reference system as an EPSG code.
#:
#: ``OGC:CRS84`` is 4326 with lon/lat axis order. Treating them as different
#: produced **five false findings** against lonboard in round 2, and no
#: consumer's harness author should have to discover that.
_CRS_ALIASES = {
    "OGC:CRS84": "EPSG:4326",
    "URN:OGC:DEF:CRS:OGC:1.3:CRS84": "EPSG:4326",
    "CRS84": "EPSG:4326",
    "WGS84": "EPSG:4326",
    "EPSG:900913": "EPSG:3857",
}


def _normalize_crs(value: Any) -> str | None:
    """Reduce a CRS spelling to a canonical ``EPSG:n`` string, or ``None``."""
    if value is None:
        return None
    if isinstance(value, int):
        return f"EPSG:{value}"

    text = str(getattr(value, "srs", value) or "").strip()
    if not text:
        return None
    upper = text.upper()
    if upper in _CRS_ALIASES:
        return _CRS_ALIASES[upper]
    if upper.startswith("EPSG:"):
        return upper
    if upper.isdigit():
        return f"EPSG:{int(upper)}"

    # Anything else -- WKT, PROJ, a pyproj CRS -- needs a real parser.
    try:
        from pyproj import CRS

        epsg = CRS.from_user_input(text).to_epsg()
    except Exception:
        return upper
    return f"EPSG:{epsg}" if epsg is not None else upper


def crs_equal(left: Any, right: Any, *, ignore_axis_order: bool = True) -> bool:
    """True when two CRS spellings name the same reference system.

    The direct remedy for round 2's five false lonboard findings: this must
    not treat ``OGC:CRS84`` and ``EPSG:4326`` as different CRSs.

    Args:
        left: A CRS as an int, a string (``"EPSG:4326"``, ``"OGC:CRS84"``,
            WKT, PROJ), a pyproj/rasterio CRS object, or ``None``.
        right: The other.
        ignore_axis_order: Treat CRS84 and 4326 as equal. ``True`` by default
            because axis order is a *representation* choice that no two
            consumers spell the same way; set it ``False`` when the axis order
            is itself under test.

    Returns:
        Whether the two name the same CRS. ``None`` equals only ``None`` --
        a missing CRS is not equal to every CRS.
    """
    if left is None or right is None:
        return left is None and right is None

    if not ignore_axis_order:
        left_text = str(getattr(left, "srs", left)).strip().upper()
        right_text = str(getattr(right, "srs", right)).strip().upper()
        if (left_text in _CRS_ALIASES) != (right_text in _CRS_ALIASES):
            return False

    return _normalize_crs(left) == _normalize_crs(right)


#: The three states a "missing" geometry can be in, which are not one state.
#:
#: Round 2 produced three separate defects living exactly in the gaps between
#: NULL, EMPTY and a NaN coordinate, and a comparator that conflates them
#: cannot see any of them.
_GEOMETRY_STATES = ("NULL", "EMPTY", "NaN-coordinate", "present")


def _geometry_state(value: Any) -> str:
    """Which of :data:`_GEOMETRY_STATES` a geometry-shaped value is in."""
    if _is_missing(value):
        return "NULL"
    if getattr(value, "is_empty", False):
        return "EMPTY"
    try:
        import numpy as np
        import shapely

        coords = shapely.get_coordinates(value)
        if coords.size and bool(np.isnan(coords).any()):
            return "NaN-coordinate"
    except Exception:
        return "present"
    return "present"


def compare_geometries(left: Any, right: Any) -> str | None:
    """Compare two geometries, distinguishing NULL, EMPTY and NaN coordinates.

    Returns a description of the difference, or ``None`` if they agree.

    The three-way distinction is the point. A comparator that folds them into
    "missing" reports agreement on all three of round 2's defects, and a
    comparator that folds them into "different" reports a finding on every
    curated empty geometry in the corpus.

    Two NaN geometries agree, for the same reason two NaN pixels do in
    :func:`compare_arrays`: a NaN that *moved* is still a divergence, but a
    NaN in the same place is a shared convention.
    """
    left_state = _geometry_state(left)
    right_state = _geometry_state(right)
    if left_state != right_state:
        return f"geometry state differs: {left_state} vs {right_state}"

    if left_state != "present":
        # Same non-present state on both sides. EMPTY still carries a type,
        # and NaN geometries compare by their (NaN-bearing) WKT.
        if left_state == "NULL":
            return None
        left_text, right_text = str(left), str(right)
        if left_text != right_text:
            return f"{left_state} geometries differ: {left_text} vs {right_text}"
        return None

    if _values_equal(left, right):
        return None
    return f"geometry differs: {left!r} vs {right!r}"


# ---------------------------------------------------------------------------
# Plan 38 Phase 3.3 -- a divergence needs an explanation, not just a count
# ---------------------------------------------------------------------------

#: Below this, two coordinates disagree by less than a micrometre on the
#: ground, which is float noise rather than a finding.
_FLOAT_NOISE_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ProbeExplanation:
    """A machine-readable explanation for a *class* of divergence.

    :attr:`CaseMetadata.known_divergences` does this for cases; this does it
    for probes. Round 2's pyproj sweep fired four probes and all four were
    expected behaviour. Without a keyed record every run re-investigates the
    same four, and the fifth, real one is buried.

    Attributes:
        key: Stable identifier, so a repeat run classifies automatically.
        description: Why this class of disagreement is expected.
        matches: ``(detail, left, right) -> bool``. Deliberately given the raw
            values as well as the message, because "these two numbers differ
            by 1e-9" is not decidable from prose.
    """

    key: str
    description: str
    matches: Callable[[str, Any, Any], bool]


def _both_numbers(left: Any, right: Any) -> bool:
    return isinstance(left, int | float) and isinstance(right, int | float)


def _is_longitude_wrap(detail: str, left: Any, right: Any) -> bool:
    if not _both_numbers(left, right):
        return False
    return (
        abs(abs(float(left)) - 180.0) < 1e-9
        and abs(abs(float(right)) - 180.0) < 1e-9
        and float(left) != float(right)
    )


def _is_pole_longitude(detail: str, left: Any, right: Any) -> bool:
    lowered = detail.lower()
    return "pole" in lowered or "latitude 90" in lowered


def _is_float_noise(detail: str, left: Any, right: Any) -> bool:
    if not _both_numbers(left, right):
        return False
    difference = abs(float(left) - float(right))
    return 0.0 < difference <= _FLOAT_NOISE_TOLERANCE


def _is_identity_transform(detail: str, left: Any, right: Any) -> bool:
    lowered = detail.lower()
    return "same crs" in lowered or "identity transform" in lowered


#: The four classes round 2's pyproj sweep fired on, all expected behaviour.
PROBE_EXPLANATIONS: tuple[ProbeExplanation, ...] = (
    ProbeExplanation(
        key="longitude_wrap",
        description=(
            "Longitude wrapping to [-180, 180]: +180 and -180 are the same "
            "meridian, and which one a library returns is a convention."
        ),
        matches=_is_longitude_wrap,
    ),
    ProbeExplanation(
        key="pole_undefined_longitude",
        description=(
            "At the pole longitude is undefined, so any value is correct and "
            "two libraries returning different ones have not disagreed."
        ),
        matches=_is_pole_longitude,
    ),
    ProbeExplanation(
        key="float_noise",
        description=(
            "Sub-micrometre disagreement: below the precision any of these "
            "transformations claims, so it is representation, not an answer."
        ),
        matches=_is_float_noise,
    ),
    ProbeExplanation(
        key="identity_transform",
        description=(
            "Source and target CRS are the same, so the probe cannot "
            "discriminate: any difference is in the harness, not the library."
        ),
        matches=_is_identity_transform,
    ),
)


def explain_divergence(
    detail: str,
    *,
    left: Any = None,
    right: Any = None,
    explanations: Iterable[ProbeExplanation] = PROBE_EXPLANATIONS,
) -> ProbeExplanation | None:
    """Return the shipped explanation for this divergence, or ``None``.

    ``None`` is the interesting answer: it is the divergence nobody has
    classified yet, which is the only kind worth a person's afternoon.
    """
    for explanation in explanations:
        try:
            if explanation.matches(detail, left, right):
                return explanation
        except Exception:  # a bad predicate must not abort the run
            continue
    return None
