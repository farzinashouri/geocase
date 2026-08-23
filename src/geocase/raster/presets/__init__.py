"""Spec-accurate product presets, built over the primitive.

Presets are a convenience, never the only door. The radiometric facts they
encode come from ``geofacts``, which machine-checks them against real ESA
product metadata — so the spec table has exactly one home and this package is
its first consumer.

Two constraints from the evaluations:

* **Default size is 256**, above the 224 px floor a ViT pipeline needs. A 32×32
  L2A fixture is spec-accurate and useless (Plan 20 trap 9).
* **S1/SAR is frozen.** :func:`sentinel1_grd` ports across and is not extended;
  three evaluated repos treat SAR as dead weight and the one compute-side
  adopter ranks the ML-EO tables ahead of it.

If a preset's product model does not match your input contract — a stretched
uint8 quicklook, an internal visualisation RGB — do not use it. Build what you
actually consume with :func:`geocase.raster.raster_fixture`; a spec-accurate
fixture that is wrong for your contract is worse than none, because it looks
plausible while testing the wrong thing.
"""

from geocase.raster.presets.sentinel1 import sentinel1_grd
from geocase.raster.presets.sentinel2 import DEFAULT_SIZE, sentinel2_l2a

__all__ = ["sentinel2_l2a", "sentinel1_grd", "DEFAULT_SIZE"]
