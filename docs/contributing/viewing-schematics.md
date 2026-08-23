# Viewing the catalog schematics

Each generated case page carries a small SVG schematic of the case's geometry — a polygon,
a line, a raster grid — rendered from `scripts/generate_catalog_pages.py`.

**Those schematics do not render on GitHub or GitLab.** If you open a case page in a
repository file browser, you will see two lines of text where the shape should be:

```
Schematic of a Polygon geometry
Schematic: Polygon geometry. Shape is illustrative, not the fixture's coordinates.
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
INFO - [12:00:00] Serving on http://127.0.0.1:8000/
```

### 3. Open a case page

Navigate to a case with a distinctive shape, for example:

```
http://127.0.0.1:8000/_generated/catalog/cases/dateline_crossing_polygon/
```

Or browse **Case Catalog** in the site navigation and pick any case.

### 4. Confirm what you should see

A correctly rendering page shows, top to bottom:

- a row of small badges — `vector`, `GeoJSON`, `Polygon`, `EPSG:4326`, `tiny`, `bundled`
- **a teal quadrilateral inside a faint rounded border** — the schematic itself
- the caption line beneath it
- the properties table, usage snippet, and risk-type links

If you see the caption but no shape, the stylesheet did not load — confirm `extra_css` in
`mkdocs.yml` still lists `stylesheets/catalog.css`.

Use the light/dark toggle in the site header to check both themes. The stroke shifts from
dark teal (`#00695c`) to light teal (`#4db6ac`); a shape that vanishes in one mode means a
custom property is missing a counterpart in `catalog.css`.

`mkdocs serve` rebuilds on save, so edits to the stylesheet or the generator appear on
refresh.

## Option B — view them on the published site

Once Plan 12 is complete, the same pages are served at:

```
https://farzinashouri.github.io/geocase
```

That URL is already the canonical `site_url` in `mkdocs.yml`, and it is baked into the
JSON-LD of every generated case page. Publication status is tracked in
[`docs/plans/archive/12-docs-site-publication.md`](../plans/archive/12-docs-site-publication.md) — until
the GitHub Actions deploy in that plan is in place, the URL will not resolve and Option A
is the only way to see the schematics.

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

The case pages are generated, and carry a `Do not edit by hand` marker. After changing
`scripts/generate_catalog_pages.py`:

```
python scripts/generate_catalog_pages.py          # rewrite the pages
python scripts/generate_catalog_pages.py --check  # confirm the gate agrees
python -m mkdocs build --strict                   # confirm the site still builds
```

Commit the regenerated pages with the generator change, or the `catalog_validation` CI job
fails against the stale output.
