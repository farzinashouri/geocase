"""Spec-accurate synthetic EO product generators (Plan 18 Phase 1).

Scope is deliberately S2 L2A and S1 GRD only (plan trap 5). Constants live in
:mod:`geocase.synth.spec` and are machine-checked against vendored real
product metadata by ``tests/synth/test_spec_fidelity.py``.
"""

from geocase.synth.sentinel1 import sentinel1_grd
from geocase.synth.sentinel2 import sentinel2_l2a

__all__ = ["sentinel1_grd", "sentinel2_l2a"]
