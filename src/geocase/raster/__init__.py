"""Raster fixtures: a low-level primitive, adversarial axes, and presets.

Replaces ``geocase.synth``. The change of shape is the point — three evaluations
said spec-accurate products should not be the API:

* Rejector B's analytics stack consumed an internal stretched-uint8
  visualisation RGB. A spec-accurate L2A fixture *would have been wrong for
  their input contract* — "worse than nothing, because it looks plausible while
  testing the wrong thing."
* Rejector C wanted "array and geotransform, build it however you like".
* The adopter needed ≥224 px, which a fixed-size preset cannot give.

So :func:`raster_fixture` is the API and presets sit above it, never as the only
door.

    from geocase.raster import raster_fixture
    from geocase.raster.axes import nodata_border
    from geocase.raster.presets import sentinel2_l2a
"""

from geocase.raster.primitive import (
    DEFAULT_SIZE,
    MIN_USEFUL_SIZE,
    FixtureSpec,
    raster_fixture,
)

__all__ = [
    "raster_fixture",
    "FixtureSpec",
    "DEFAULT_SIZE",
    "MIN_USEFUL_SIZE",
]
