"""Perfect-answer edge-case tests for the easy interview utilities."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SUPPORT_PATH = Path(__file__).with_name("_easy_geospatial_interview_test_support.py")
_SUPPORT_SPEC = importlib.util.spec_from_file_location(
    "_easy_geospatial_interview_test_support_perfect",
    _SUPPORT_PATH,
)
if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
    raise ImportError(f"Could not load test support module from {_SUPPORT_PATH}")

_SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
_SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)

for _name, _value in vars(_SUPPORT_MODULE).items():
    if _name.startswith("test_") and "_perfect" in _name:
        globals()[_name] = _value

del _name, _value
