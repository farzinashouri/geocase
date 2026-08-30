# UTM Zone 56S Polygon (Sydney)

## The false northing

Southern-hemisphere UTM zones carry a **10 000 000 m false northing**, so that
coordinates stay positive south of the equator. The northings in this file are
around 6 260 000 -- meaning roughly 3 740 000 m *south* of the equator, not
6 260 km north of it.

That single fact is the case's whole point, and it fails in a specific,
recognisable way: a consumer that treats EPSG:327xx as EPSG:326xx (or that
hard-codes the northern variant when deriving a zone code from a longitude)
places this polygon in Siberia rather than New South Wales. The error is
thousands of kilometres and the wrong hemisphere, but the numbers stay
plausible-looking throughout, so nothing crashes.

## Why it was missing

Every UTM case in the bundled catalog previously resolved to zone 33N. There
was no southern-hemisphere fixture at all, which meant the false northing --
the single most common UTM mistake -- was untested by construction.

## What to assert

Reproject to EPSG:4326 and check the latitude is negative and near -33.7. See
also `utm_zone_1n_small` (zone edge) and `utm_zone_boundary_straddle`
(cross-zone).
