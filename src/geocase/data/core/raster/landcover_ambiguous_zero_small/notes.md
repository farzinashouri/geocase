# Land Cover With Ambiguous Zero

A 16×16 single-band `uint8` categorical land-cover raster in EPSG:32633, with a
colormap, declaring `nodata = 0`.

## The ambiguity

The class scheme is:

| Value | Meaning |
|---|---|
| 0 | unclassified / bare — **and** the declared NoData sentinel |
| 1 | water |
| 2 | vegetation |
| 3 | urban |

An 8×8 block of genuine 0 pixels sits in the middle of the scene, surrounded by
classes 1, 2 and 3. Those zeros are real, meaningful data. They are also, by the
file's own declaration, NoData.

There is no way to tell the two apart from the file alone. That
indistinguishability *is* the case — not a defect in the fixture to be cleaned
up. Two reasonable consumers disagree about the same pixels:

- one masking `data == nodata` silently deletes an entire legitimate class, and
  reports 25% of the scene as missing;
- one ignoring NoData treats sentinel pixels as classified data.

Neither can be shown wrong from the file. Real land-cover products ship this
way, which is why "just read the nodata tag" is not a sufficient answer.

## The sibling

`landcover_small` is the same scene with the ambiguity
removed: every pixel is classified, and the raster deliberately declares no
NoData at all. The pair is the useful artifact. Run the same code over both and
any difference in behaviour is the ambiguity acting on it, isolated from every
other property (CRS, dtype, shape, compression and colormap are identical).

## Regeneration

Emitted by `scripts/generate_raster_fixtures.py` from the same array that
produces `landcover_small`, with the 0 block written in and `nodata=0`
declared. There is no hand-committed payload here — see
`docs/plans/32-footprint-truth-and-ambiguous-zero.md` Phase 2, and Plan 28 for
why every fixture must sit inside the regeneration gate.
