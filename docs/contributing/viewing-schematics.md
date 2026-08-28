# Viewing the catalog diagrams

Each generated case page carries a small SVG diagram — a polygon, a line, a raster grid —
rendered from `scripts/generate_catalog_pages.py`.

**Vector cases show their real geometry.** The generator loads each case through
`geocase.load_case(id).load()` and projects its actual coordinates into the diagram
viewport (`scripts/catalog_geometry.py`), so
`dateline_crossing_polygon` and `simple_valid_polygon` are visibly different pictures.
Raster and NetCDF diagrams remain *schematics* drawn from metadata; they are not pictures
of the pixels.

A handful of cases are deliberately malformed and cannot be loaded at all —
`unclosed_ring_polygon` is the current example. Those fall back to a generic shape for
their geometry type, and the caption says so explicitly rather than claiming a provenance
the drawing does not have.

**Neither kind renders on GitHub or GitLab.** If you open a case page in a repository file
browser, you will see two lines of text where the shape should be:

```
Polygon geometry of dateline_crossing_polygon, rendered from the case's data
Polygon geometry, rendered from the case's actual geometry. Scale is normalized to the viewport…
```

That is expected, and it is not a bug in the diagram. This page explains why, and gives
the two ways to actually see the shapes.

## Why the repository browser cannot show them

Two independent reasons, either of which alone would be enough:

1. **Both hosts strip inline `<svg>` from rendered Markdown.** It is a security measure —
   inline SVG can carry scripts. The `<title>` and `<figcaption>` text inside the element
   survives the sanitizer, which is exactly why you see captions with no picture.
2. **The schematics are themed by stylesheet.** The SVG paints itself with CSS custom
   properties — `var(--gc-diagram-stroke)` and `var(--gc-diagram-fill)` — that are defined
   in [`docs/stylesheets/catalog.css`](../stylesheets/catalog.css) and swap values between
   light and dark mode. A file browser loads no stylesheet, so even an unsanitized SVG
   would draw with no stroke and no fill.

The schematics are built for the mkdocs site. Render the site and they appear.

## Option A — view them locally

Nothing needs to be published for this, and it takes about a minute.

### 1. Install the docs dependencies

From the repository root:

```
python -m pip install -e ".[docs]"
```

The `docs` extra is self-contained — `mkdocs>=1.5` and `mkdocs-material>=9.0` — and pulls
in none of the project's geospatial dependencies. You do not need `geopandas` or
`rasterio` installed to read the docs.

### 2. Start the live server

```
python -m mkdocs serve
```

Watch for the line reporting the address, usually:

```
INFO - [12:00:00] Serving on http://127.0.0.1:8000/geocase/
```

### 3. Open a case page

Navigate to a case with a distinctive shape, for example:

```
http://127.0.0.1:8000/geocase/_generated/catalog/cases/dateline_crossing_polygon/
```

Or browse **Case Catalog** in the site navigation and pick any case.

### 4. Confirm what you should see

A correctly rendering page shows, top to bottom:

- a row of small badges — `vector`, `GeoJSON`, `Polygon`, `EPSG:4326`, `tiny`, `bundled`
- **a teal shape inside a faint rounded border** — the diagram itself. For
  `dateline_crossing_polygon` that is a wide, squat rectangle: its real bounds span 20° of
  longitude by 10° of latitude
- the caption line beneath it, naming whether the shape is real geometry or a fallback
- the properties table, usage snippet, and risk-type links

If you see the caption but no shape, the stylesheet did not load — confirm `extra_css` in
`mkdocs.yml` still lists `stylesheets/catalog.css`.

Use the light/dark toggle in the site header to check both themes. The stroke shifts from
dark teal (`#00695c`) to light teal (`#4db6ac`); a shape that vanishes in one mode means a
custom property is missing a counterpart in `catalog.css`.

`mkdocs serve` rebuilds on save, so edits to the stylesheet or the generator appear on
refresh.

## Option B — view them on the published site

Once GitHub Pages is enabled for the repository, the same pages are served at:

```
https://farzinashouri.github.io/geocase
```

That URL is the canonical `site_url` in `mkdocs.yml`, and it is baked into the JSON-LD of
every generated case page. The GitHub Actions deployment workflow publishes the same strict
MkDocs build used in CI. Until GitHub Pages is enabled in the repository settings, Option A
is the way to see the schematics.

## Producing a static copy

To hand someone the rendered pages without running a server:

```
python -m mkdocs build --strict
```

This writes a complete static site to `site/`, which is gitignored. Open
`site/_generated/catalog/cases/dateline_crossing_polygon/index.html` directly in a browser
— the schematics render, because the stylesheet is alongside it.

`--strict` turns broken links and other warnings into failures, which is the same gate CI
applies. A clean build prints `Documentation built in …` with no warnings above it.

## If you regenerate the pages

The case pages are generated, and carry a `Do not edit by hand` marker.

**Regenerating needs the vector stack**, because the generator loads each case to draw it.
Run it from the conda `geocase` environment. Without `geopandas` the generator still works
but every vector diagram silently degrades to a fallback archetype, which would commit a
whole catalog of wrong pages. The `catalog` CI job installs `.[raster,vector]`, so the gate
compares against the real previews.

After changing `scripts/generate_catalog_pages.py` or `scripts/catalog_geometry.py`:

```
python scripts/generate_catalog_pages.py          # rewrite the pages
python scripts/generate_catalog_pages.py --check  # confirm the gate agrees
python -m mkdocs build --strict                   # confirm the site still builds
```

Commit the regenerated pages with the generator change, or the `catalog_validation` CI job
fails against the stale output.
