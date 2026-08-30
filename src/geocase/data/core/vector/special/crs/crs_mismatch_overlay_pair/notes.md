# CRS Mismatch Overlay Pair

## The construction

One ground footprint -- 11.6E-11.8E, 59.9N-60.05N, in southeastern Norway,
comfortably inside UTM zone 33N -- written **twice, into two files**:

| file | declared CRS | actual ordinates | honest |
|---|---|---|---|
| `reference_wgs84.geojson` (primary) | `urn:ogc:def:crs:OGC:1.3:CRS84` | degrees | yes |
| `mismatched_utm33.geojson` (sidecar) | `urn:ogc:def:crs:EPSG::4326` | UTM 33N metres | **no** |

The sidecar's SW corner is `309839.329, 6645158.002`. Those are eastings and
northings, and the file claims they are longitude and latitude.

**Both files are individually well-formed.** Each is valid GeoJSON, each parses
without a warning, and neither is internally inconsistent in any way a
single-file validator can see. That is the point: a CRS mismatch is a
relationship between two inputs, and no amount of checking one file finds it.

## Why two files rather than two features

`utm_zone_33n_to_32n_pair` stores its pair as two features in one collection,
because a GeoJSON FeatureCollection has exactly one CRS and that case needed
both halves directly comparable. Here that constraint is inverted: the
**disagreeing declarations are the subject**, so the two halves cannot share a
collection. Hence one case with a sidecar.

They stay one case rather than two because a relationship split across two
independently-selectable ids can be selected apart, and a selector that returns
half a relationship is a footgun.

## What to assert

Reproject the sidecar from its *true* CRS (`params.sidecar_true_epsg`, 32633)
to WGS84 and the corners land on the reference within
`params.agreement_tolerance_m` (1 m; measured at 0.0004 m). That agreement is
what makes the two files the same footprint rather than two unrelated shapes.

Then do what a naive consumer does -- read the sidecar's ordinates as the
degrees it declares. The SW corner lands **3359 km** away, past the north pole
after normalisation. Nothing raises. The catalog's contract is
`params.naive_overlay_error_min_km` (3000 km), a floor rather than the exact
figure so the assertion is not brittle against a re-projection.

An overlay, spatial join or clip that trusts each input's declaration produces
an empty result here -- which reads as "no features intersect" rather than as
an error, and is the failure mode worth testing for.

## Related

`utm_zone_33n_to_32n_pair` covers zone *selection* between two adjacent, both
correctly declared zones. `rasterize_match_wgs84_polygon` and
`web_mercator_baseline` are the single-layer CRS cases; neither can express a
mismatch, which is why this case exists.
