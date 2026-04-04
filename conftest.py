from __future__ import annotations

from importlib import metadata
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _has_geocase_pytest_entry_point() -> bool:
    try:
        metadata.version("geocase")
    except metadata.PackageNotFoundError:
        return False
    return True


pytest_plugins = [] if _has_geocase_pytest_entry_point() else ["geocase.pytest_plugin"]
