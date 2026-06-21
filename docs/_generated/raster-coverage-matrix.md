### Raster coverage matrix (current vs target)

Total bundled raster cases scanned: **13**.
Cases declaring typed band-count expectations: **5/13**.

#### A) Product families

| Product family | Current coverage | Target |
|---|---:|---:|
| Optical / RGB | ✅ 1 case(s) | ✅ required |
| Multispectral | ✅ 1 case(s) | ✅ required |
| Mask | ✅ 2 case(s) | ✅ required |
| DEM / Terrain | ✅ 1 case(s) | ✅ required |
| Derived index (NDVI) | ✅ 1 case(s) | ✅ required |
| SAR / Radar | ❌ missing | ✅ required |
| COG | ✅ 1 case(s) | ✅ required |

#### B) Data types

| dtype | Current coverage | Target |
|---|---:|---:|
| uint8 | ✅ present | ✅ required |
| uint16 | ✅ present | ✅ required |
| int16 | ❌ missing | ✅ required |
| int32 | ❌ missing | ✅ required |
| float32 | ✅ present | ✅ required |
| float64 | ❌ missing | ✅ required |

#### C) Delivery styles

| Delivery style | Current coverage | Target |
|---|---:|---:|
| Single-file GeoTIFF | ✅ present | ✅ required |
| Internal overviews / COG | ✅ present | ✅ required |
| External overviews | ❌ missing | ✅ required |
| Compression variants | ❌ missing | ✅ required |
