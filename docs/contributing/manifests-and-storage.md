# Manifests and Storage Support

> **Status (August 2026):** Manifest support is **implemented**. Storage transport is
> **deliberately deferred to v1.1** — not unfinished, but declined for v1.0 with a
> specific condition for reopening it.
>
> Manifests parse, validate, and resolve: `catalog/manifests.py` loads them, the registry
> merges their ids with the bundled catalog, `GEOCASE_MANIFESTS` selects which files are
> read (the resolved paths are part of the registry cache key), and
> `scripts/validate_catalog.py` gates them in CI — catching shadowed ids, cross-manifest
> duplicates, malformed digests, and dangling `bundled_analog` references. Remote cases
> are discoverable through the public API: `show_case` describes one, and `materialize_case`
> refuses it with an actionable error rather than an internal `KeyError`.
>
> Transport — download, cache, unpack, verify — does not exist. That is the decision, and
> the reason is that there is no cargo. Both manifests are 100% placeholder: every `sha256`
> is the literal `replace_me`, every `base_uri` points at `example.org`, and nothing has
> ever been published. Building a transport layer whose only user would be its own tests
> ships a maintenance burden and an implied promise in exchange for nothing.
>
> **The v1.1 gate is concrete: at least one real published archive with a real sha256.**
> Until that exists, the honest surface is a catalog that knows what it cannot give you and
> says so clearly.

This page explains what **manifest support** and **storage support** mean in
GeoCase, why they are different, and why both matter.

If you are reading the roadmap and wondering why “implement manifest support”
appears before or alongside storage work, this is the reason: manifests are the
**catalog/discovery layer**, while storage is the **transport/materialization
layer**.

Another way to think about it:

- the **bundled core catalog** is the bookshelf already in your room,
- the **manifest** is the library catalog telling you which other books exist,
- and the **storage layer** is the delivery service that brings those books to
  you and checks that the shipment is correct.

You can have a useful catalog before delivery exists. But delivery without a
catalog is much less useful, because you do not know what is available or what
you are supposed to ask for.

For the current implementation sequence and scope boundaries, see
[`development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md). The original manifest plan is retained as
an implementation log in
[`../plans/archive/06-manifest-support.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/archive/06-manifest-support.md).

---

## The short version

- **Manifest support** tells GeoCase which external cases exist.
- **Storage support** tells GeoCase how to fetch, cache, verify, and expose
  those external files locally.
- **Manifest without storage** is still useful for discovery, validation, and
  unified catalog views.
- **Storage without manifest** is much less useful because GeoCase still does
  not know what it is supposed to fetch.

---

## What a manifest is in GeoCase

A manifest is a metadata file that describes an **external catalog** of cases
that are **not bundled inside** `src/geocase/data/`.

The bundled core catalog works well for small, self-contained fixtures. But
some datasets are too large, too numerous, or too organization-specific to ship
inside the package. Manifests let GeoCase reference those cases without copying
them into the core package.

The repository already contains an example manifest:

- `extended-manifests/public-extended.yaml`

That file describes a public extended catalog with a shared storage block and a
list of cases.

Example excerpt:

```yaml
storage:
  storage_type: https
  base_uri: https://example.org/geocase/public
  requires_auth: false
  is_public: true

cases:
  - case_id: coastal_scene_small
    version: "1.0.0"
    relative_path: coastal_scene_small.zip
    sha256: "replace_me"
    byte_size: 1280000
    archive_format: zip
```

From this alone, GeoCase can learn several important things:

- a case called `coastal_scene_small` exists,
- it belongs to the `public-extended` manifest,
- its artifact is expected at `coastal_scene_small.zip`,
- it is versioned,
- it has an expected size,
- it should eventually have a checksum,
- and it is delivered as a zip archive.

That is already meaningful information, even before any download logic exists.

---

## What manifest support means in code

In runtime terms, manifest support means implementing logic in:

- `src/geocase/catalog/manifests.py`

so that GeoCase can:

- read manifest YAML files,
- validate their structure,
- expose manifest entries as part of the catalog,
- merge bundled and extended cases into one logical registry view,
- tell the user whether a case is bundled or external,
- and surface enough metadata to make later fetching possible.

Manifest support is mainly about **catalog understanding**.

---

## What storage support means in GeoCase

Storage support is the layer that turns manifest metadata into actual local
files that loaders can open.

In GeoCase, that work is intended to live in:

- `src/geocase/storage/local.py`
- `src/geocase/storage/remote.py`
- `src/geocase/storage/cache.py`
- `src/geocase/storage/hashing.py`

This layer is responsible for questions like:

- Where should a downloaded case live on disk?
- If the file is already cached, can it be reused?
- How is a remote URL resolved from the manifest?
- If the dataset is zipped, where is it unpacked?
- How is the checksum verified?
- What happens if the file is missing or corrupted?

Storage support is mainly about **materialization and trust**.

---

## Why both are needed

GeoCase’s long-term design is “small bundled core, larger optional catalog.”

That requires two different capabilities:

1. **Knowing what exists**
2. **Being able to fetch or resolve it**

Manifests solve the first problem.
Storage solves the second.

If GeoCase only has manifests:

- it can understand the extended catalog,
- but it cannot yet retrieve the files.

If GeoCase only has storage code:

- it may know how to download something,
- but it still does not know which case IDs exist,
- what file belongs to which case,
- what checksum is expected,
- or whether the artifact is zipped.

That is why the two layers are related but not interchangeable.

---

## Why manifest support is still useful by itself

It is easy to think “manifest support is not useful until storage exists,” but
that is too strong.

Manifest support alone already enables several useful workflows.

### 1. Unified catalog discovery

GeoCase could show a case like `coastal_scene_small` in the same catalog view
as bundled cases, even if the file is not yet local.

For example, a future `list_cases()` or `show_case()` could display:

- `case_id`: `coastal_scene_small`
- source: `public-extended`
- storage type: `https`
- archive: `coastal_scene_small.zip`
- byte size: `1280000`
- state: `remote, not fetched`

That is already meaningful for users and maintainers.

### 2. Validation and review

Manifests give maintainers a structured way to review external catalog entries
before download logic exists.

For example, GeoCase could validate:

- duplicate `case_id` values,
- missing `relative_path`,
- invalid `sha256` format,
- unsupported `archive_format`,
- malformed storage blocks,
- or a manifest that references a case ID already defined elsewhere.

This makes external catalogs safer and easier to maintain.

### 3. Planning and metadata-only workflows

Sometimes users need to know **what would be fetched** before actually doing it.

Manifest support enables preflight behavior like:

- “This case is remote.”
- “It will download from HTTPS.”
- “It is about 1.5 MB.”
- “It expects checksum X.”
- “It arrives as a zip archive.”

That can be useful in CI planning, documentation, contributor workflows, and
future CLI/UI features.

### 4. Separation of bundled versus extended catalogs

Without manifests, the only way to grow the catalog is to keep adding cases to
the bundled core index. That does not scale well for larger raster scenes,
archives, or private datasets.

Manifests provide a clean way to say:

- the **core package** stays small,
- the **extended catalog** stays external,
- but both are still part of the same logical GeoCase universe.

#### The bundled/remote raster boundary

Raster is where this separation bites first, so the boundary is written down
explicitly in `extended-manifests/satellite-scenes.yaml`:

- **Bundled** raster fixtures (`src/geocase/data/core/raster/`) stay `tiny` or
  `small` and exist to cover *structure* — dtypes, nodata conventions, band
  counts, CRS/tiling edge cases, COG layout.
- **Remote** raster scenes stay in the `satellite-scenes` manifest and exist to
  cover *realism* — full-size optical, multispectral, SAR, DEM, and land-cover
  products that would bloat the package.

Each remote scene names the bundled fixture it is the realistic analog of via
`bundled_analog`:

| Remote scene | `bundled_analog` |
| --- | --- |
| `optical_rgb_scene` | `optical_rgb_small` |
| `multispectral_s2_scene` | `multispectral_s2_like_small` |
| `sar_vv_scene` | `sar_vv_small` |
| `dem_scene` | `dem_small` |
| `landcover_scene` | `landcover_small` |

That pairing means a contributor can always answer "what is the big version of
this fixture?" — and the reverse: a new realistic scene is expected to arrive
with a small bundled counterpart rather than on its own.

The manifest only *declares* these scenes. Their archives are not published yet,
so the `sha256` values are placeholders and fetching them will fail checksum
verification by design until real artifacts exist.

---

## What manifest support does **not** provide on its own

Manifest support alone does **not** let GeoCase fully use a remote case.

Without storage support, GeoCase still cannot reliably:

- download `coastal_scene_small.zip`,
- unpack it,
- cache it,
- verify the checksum against the manifest,
- or open the local files automatically.

So if the question is:

> Can a user select and load a remote case end-to-end with manifest support
> alone?

the answer is **no**.

But if the question is:

> Can GeoCase meaningfully ingest, validate, and expose external catalogs with
> manifest support alone?

the answer is **yes**.

---

## Why checksums matter

The `sha256` field in a manifest is not just decorative metadata.

Checksums are what let GeoCase say:

- “This downloaded file is exactly the one the manifest declared.”
- “The artifact was not truncated, corrupted, or silently replaced.”
- “The cache entry is still valid and does not need to be re-fetched.”

That is why checksum handling belongs to the storage layer, especially in:

- `src/geocase/storage/hashing.py`

But manifests still need to carry the checksum declaration, because storage
cannot verify what was never recorded.

So the relationship is:

- **manifest** declares the expected checksum,
- **storage/hashing** verifies the actual bytes.

---

## A concrete example: `coastal_scene_small`

Take the manifest entry in:

- `extended-manifests/public-extended.yaml`

```yaml
- case_id: coastal_scene_small
  version: "1.0.0"
  relative_path: coastal_scene_small.zip
  sha256: "replace_me"
  byte_size: 1280000
  archive_format: zip
```

### With manifest support only

GeoCase could potentially:

- list `coastal_scene_small` in the catalog,
- show that it is part of an external manifest,
- report that it is remote and not yet fetched,
- show its expected archive path and size,
- and validate whether the manifest entry is structurally correct.

### With manifest + storage support

GeoCase could additionally:

- construct the full URL from `base_uri` + `relative_path`,
- download `coastal_scene_small.zip`,
- store it in a local cache,
- verify the `sha256`,
- unpack it if needed,
- and hand the resulting local files to the normal case-loading machinery.

That is the difference between **catalog awareness** and **usable remote case
loading**.

---

## Why manifests should come before or alongside storage

If implementation is phased, manifest support is a sensible first step because
it defines the contract that storage must follow.

Storage code needs to know:

- what artifact to fetch,
- which protocol/backend to use,
- which checksum to verify,
- which archive format to expect,
- and which case ID the artifact belongs to.

That information belongs in manifests.

So the practical order is usually:

1. define the manifest structure,
2. implement manifest parsing and validation,
3. integrate manifests into the catalog view,
4. implement storage resolution and caching,
5. wire remote case loading into the normal runtime path.

This sequencing is why the roadmap can reasonably say “implement manifest
support” before “implement storage layer” without implying that manifests alone
finish the feature.

---

## How this fits the overall GeoCase architecture

GeoCase is easiest to reason about as separate layers:

- **metadata layer** — what exists
- **catalog layer** — what can be discovered and selected
- **runtime layer** — what can be loaded
- **storage layer** — where files come from and how they are trusted

Manifest support lives mostly at the boundary between the **metadata layer** and
the **catalog layer**.

Storage support lives between the **catalog/runtime layer** and the actual file
system or network.

That separation is intentional. It keeps the design simpler and makes each part
easier to test.

---

## Recommended contributor mental model

When thinking about extended datasets, use this simple model:

- **Bundled case**: already present in the package
- **Manifest entry**: a promise that an external case exists
- **Storage resolution**: the process of turning that promise into a real local
  file tree
- **Case loader**: the normal `VectorCase` / `RasterCase` / `NetCDFCase` logic
  operating on those local files

Or, even shorter:

- **manifest = catalog record**
- **storage = delivery + cache + verification**

Both are needed for the final experience, but they do different jobs.
