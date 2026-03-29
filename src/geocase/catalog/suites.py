"""Suite resolution — load a suite definition and resolve it to cases.

A suite YAML describes *which* cases to include via its ``selection``
block.  This module ties that selection to the live registry so you
can ask: "give me the cases for the core-vector suite" and get back a
ready-to-use list.
"""

from __future__ import annotations

from pathlib import Path

from geocase.catalog.loader import load_suite_index, load_suite_metadata
from geocase.catalog.models import CaseMetadata, SuiteMetadata
from geocase.catalog.registry import CaseRegistry, get_registry
from geocase.catalog.selectors import select_cases


class ResolvedSuite:
    """A suite whose selection has been evaluated against a registry.

    Attributes:
        metadata: The parsed :class:`SuiteMetadata`.
        cases: Ordered list of matching :class:`CaseMetadata`.
    """

    def __init__(
        self, metadata: SuiteMetadata, cases: list[CaseMetadata]
    ) -> None:
        self.metadata = metadata
        self.cases = cases

    @property
    def suite_key(self) -> str:
        return self.metadata.suite_key

    @property
    def case_ids(self) -> list[str]:
        return [c.id for c in self.cases]

    def __len__(self) -> int:
        return len(self.cases)

    def __repr__(self) -> str:
        return (
            f"ResolvedSuite({self.suite_key!r}, "
            f"{len(self.cases)} cases)"
        )


def resolve_suite(
    suite: SuiteMetadata,
    registry: CaseRegistry | None = None,
) -> ResolvedSuite:
    """Evaluate a suite's selection against the registry.

    Args:
        suite: Parsed suite metadata with its selection criteria.
        registry: Registry to query.  Uses the default singleton when
            *None*.

    Returns:
        A :class:`ResolvedSuite` with the matching cases, optionally
        reordered according to ``suite.case_order``.
    """
    if registry is None:
        registry = get_registry()

    all_cases = registry.list_cases()
    matched = select_cases(all_cases, suite.selection)

    # Apply explicit ordering if provided
    if suite.case_order:
        order_map = {cid: idx for idx, cid in enumerate(suite.case_order)}
        # Cases listed in case_order come first (in that order),
        # followed by any remaining matches in their original order.
        def sort_key(c: CaseMetadata) -> tuple[int, str]:
            return (order_map.get(c.id, len(suite.case_order)), c.id)

        matched = sorted(matched, key=sort_key)

    return ResolvedSuite(metadata=suite, cases=matched)


def load_and_resolve_suite(
    suite_path: Path,
    registry: CaseRegistry | None = None,
) -> ResolvedSuite:
    """Convenience: load a suite YAML and resolve it in one step.

    Args:
        suite_path: Path to a suite YAML file.
        registry: Optional registry override.

    Returns:
        A :class:`ResolvedSuite`.
    """
    suite_meta = load_suite_metadata(suite_path)
    return resolve_suite(suite_meta, registry)


def load_all_suites(
    suite_index_path: Path | None = None,
    registry: CaseRegistry | None = None,
) -> list[ResolvedSuite]:
    """Load and resolve every suite listed in suite-index.yaml.

    Args:
        suite_index_path: Path to ``suite-index.yaml``.  Defaults to
            the package's bundled index.
        registry: Optional registry override.

    Returns:
        List of :class:`ResolvedSuite` instances.
    """
    if suite_index_path is None:
        suite_index_path = (
            Path(__file__).resolve().parent.parent
            / "metadata"
            / "suite-index.yaml"
        )

    suite_index_path = Path(suite_index_path)
    base_dir = suite_index_path.parent  # metadata/

    relative_paths = load_suite_index(suite_index_path)

    resolved: list[ResolvedSuite] = []
    for rel in relative_paths:
        suite_path = (base_dir / rel).resolve()
        resolved.append(load_and_resolve_suite(suite_path, registry))

    return resolved
