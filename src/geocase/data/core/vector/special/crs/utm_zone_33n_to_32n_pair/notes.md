# UTM Zone 33N / 32N Adjacent Pair

## The construction

One ground footprint -- 11.6E-12.4E, 52.0N-52.4N, chosen to sit across the 12E
meridian that divides UTM zones 32N and 33N -- recorded as **two features**.
Both hold identical WGS84 coordinates; they differ only in the properties
recording which zone each was projected through:

| feature | source EPSG | easting of the SW corner |
|---|---|---|
| `as_recorded_in_zone_33n` | 32633 | 266 621 m |
| `as_recorded_in_zone_32n` | 32632 | 676 881 m |

Same point on the ground, eastings **412 km apart**. That is not an error; it
is what adjacent UTM zones do, and it is precisely the magnitude of the bug a
consumer produces when it mixes the two.

## What to assert

Project each feature through its own `source_epsg` and back to WGS84. The two
results must agree to within `params.agreement_tolerance_m` (1 m). A consumer
that assumes one zone for the whole dataset, or that derives the zone from a
bounding-box centroid without checking the extent crosses an edge, will
disagree by hundreds of kilometres on at least one feature.

Both features are stored in WGS84 rather than in their respective projected
CRSs deliberately: a GeoJSON FeatureCollection has one CRS, so storing them
projected would require two files and lose the direct comparability that is the
case's entire purpose.

## Related

`utm_zone_boundary_straddle` covers the single-geometry version of the same
hazard -- one polygon extending past its own zone's edge.
