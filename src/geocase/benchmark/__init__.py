"""GeoCase benchmark: silent failures in LLM-generated geospatial code.

Plan 15. Task packages live under ``tasks/``; each pairs a neutral prompt with
a first-principles oracle. ``python -m geocase.benchmark grade`` classifies a
directory of generated modules as PASS/SILENT/LOUD/MISSING per check.
"""

from geocase.benchmark.registry import all_tasks, get_task
from geocase.benchmark.taxonomy import CheckKind, CheckResult, Status, TrialOutcome

__all__ = [
    "CheckKind",
    "CheckResult",
    "Status",
    "TrialOutcome",
    "all_tasks",
    "get_task",
]
