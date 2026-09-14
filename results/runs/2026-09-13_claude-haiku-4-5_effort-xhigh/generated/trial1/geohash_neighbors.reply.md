```python
def geohash_neighbors(gh):
    """Return the geohashes of the 8 cells surrounding the given geohash.
    
    East and west neighbours wrap across the antimeridian; cells beyond
    the poles are omitted.
    """
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def decode_exact(gh):
        """Decode geohash to get bounding box (lat_min, lat_max, lon_min, lon_max)."""
        lat_min, lat_max = -90.0, 90.0
        lon_min, lon_max = -180.0, 180.0
        is_even = True
        
        for c in gh:
            idx = BASE32.index(c)
            for i in range(4, -1, -1):
                bit = (idx >> i) & 1
                if is_even:
                    lon_mid = (lon_min + lon_max) / 2
                    if bit == 1:
                        lon_min = lon_mid
                    else:
                        lon_max = lon_mid
                else:
                    lat_mid = (lat_min + lat_max) / 2
                    if bit == 1:
                        lat_min = lat_mid
                    else:
                        lat_max = lat_mid
                is_even = not is_even
        
        return lat_min, lat_max, lon_min, lon_max
    
    def encode(lat, lon, precision):
        """Encode lat/lon to geohash with given precision."""
        lat_min, lat_max = -90.0, 90.0
        lon_min, lon_max = -180.0, 180.0
        geohash = []
        ch = 0
        bit = 0
        is_even = True
        
        while len(geohash) < precision:
            if is_even:
                mid = (lon_min + lon_max) / 2
                if lon > mid:
                    ch |= (1 << (4 - bit))
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2
                if lat > mid:
                    ch |= (1 << (4 - bit))
                    lat_min = mid
                else:
                    lat_max = mid
            
            is_even = not is_even
            bit += 1
            
            if bit == 5:
                geohash.append(BASE32[ch])
                ch = 0
                bit = 0
        
        return ''.join(geohash)
    
    lat_min, lat_max, lon_min, lon_max = decode_exact(gh)
    lat_center = (lat_min + lat_max) / 2
    lon_center = (lon_min + lon_max) / 2
    lat_size = lat_max - lat_min
    lon_size = lon_max - lon_min
    
    precision = len(gh)
    neighbors = []
    
    for dlat, dlon in [
        (lat_size, 0),           # N
        (lat_size, lon_size),    # NE
        (0, lon_size),           # E
        (-lat_size, lon_size),   # SE
        (-lat_size, 0),          # S
        (-lat_size, -lon_size),  # SW
        (0, -lon_size),          # W
        (lat_size, -lon_size),   # NW
    ]:
        new_lat = lat_center + dlat
        new_lon = lon_center + dlon
        
        if new_lat < -90 + lat_size / 2 or new_lat > 90 - lat_size / 2:
            continue
        
        while new_lon < -180:
            new_lon += 360
        while new_lon >= 180:
            new_lon -= 360
        
        neighbors.append(encode(new_lat, new_lon, precision))
    
    return neighbors
```