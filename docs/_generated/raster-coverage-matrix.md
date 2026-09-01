### Raster coverage matrix (current vs target)

Total bundled raster cases scanned: **37**.
Cases declaring typed band-count expectations: **24/37**.

#### A) Product families

| Product family | Current coverage | Target |
|---|---:|---:|
| Optical / RGB | ✅ 4 case(s) | ✅ required |
| Multispectral | ✅ 3 case(s) | ✅ required |
| Mask | ✅ 4 case(s) | ✅ required |
| DEM / Terrain | ✅ 7 case(s) | ✅ required |
| Derived index (NDVI) | ✅ 2 case(s) | ✅ required |
| SAR / Radar | ✅ 2 case(s) | ✅ required |
| COG | ✅ 4 case(s) | ✅ required |

#### B) Data types

| dtype | Current coverage | Target |
|---|---:|---:|
| uint8 | ✅ present | ✅ required |
| uint16 | ✅ present | ✅ required |
| int16 | ✅ present | ✅ required |
| int32 | ❌ missing | ✅ required |
| float32 | ✅ present | ✅ required |
| float64 | ❌ missing | ✅ required |

#### C) Delivery styles

| Delivery style | Current coverage | Target |
|---|---:|---:|
| Single-file GeoTIFF | ✅ present | ✅ required |
| Internal overviews / COG | ✅ present | ✅ required |
| External overviews | ✅ present | ✅ required |
| Compression variants | ❌ missing | ✅ required |
