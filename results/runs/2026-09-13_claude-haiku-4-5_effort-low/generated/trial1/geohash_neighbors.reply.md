```python
def geohash_neighbors(gh):
    """
    Get the 8 neighboring geohashes of the same precision.
    Neighbors wrap across the antimeridian but not across poles.
    """
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def decode(geohash):
        """Decode geohash to (lat_min, lat_max, lon_min, lon_max)"""
        lat_min, lat_max = -90.0, 90.0
        lon_min, lon_max = -180.0, 180.0
        is_lon = True
        
        for c in geohash:
            idx = BASE32.index(c)
            for i in range(4, -1, -1):
                bit = (idx >> i) & 1
                if is_lon:
                    mid = (lon_min + lon_max) / 2
                    if bit:
                        lon_min = mid
                    else:
                        lon_max = mid
                else:
                    mid = (lat_min + lat_max) / 2
                    if bit:
                        lat_min = mid
                    else:
                        lat_max = mid
                is_lon = not is_lon
        
        return lat_min, lat_max, lon_min, lon_max
    
    def encode(lat, lon, precision):
        """Encode a point to geohash"""
        lat_min, lat_max = -90.0, 90.0
        lon_min, lon_max = -180.0, 180.0
        geohash = []
        is_lon = True
        bits = 0
        bit = 0
        
        while len(geohash) < precision:
            if is_lon:
                mid = (lon_min + lon_max) / 2
                if lon >= mid:
                    bits |= (1 << (4 - bit))
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2
                if lat >= mid:
                    bits |= (1 << (4 - bit))
                    lat_min = mid
                else:
                    lat_max = mid
            
            is_lon = not is_lon
            bit += 1
            
            if bit == 5:
                geohash.append(BASE32[bits])
                bits = 0
                bit = 0
        
        return ''.join(geohash)
    
    lat_min, lat_max, lon_min, lon_max = decode(gh)
    precision = len(gh)
    
    lat_center = (lat_min + lat_max) / 2
    lon_center = (lon_min + lon_max) / 2
    lat_size = lat_max - lat_min
    lon_size = lon_max - lon_min
    
    neighbors = []
    
    for dlat in [-1, 0, 1]:
        for dlon in [-1, 0, 1]:
            if dlat == 0 and dlon == 0:
                continue
            
            new_lat = lat_center + dlat * lat_size
            new_lon = lon_center + dlon * lon_size
            
            while new_lon > 180:
                new_lon -= 360
            while new_lon < -180:
                new_lon += 360
            
            if new_lat < -90 or new_lat > 90:
                continue
            
            neighbor = encode(new_lat, new_lon, precision)
            neighbors.append(neighbor)
    
    return neighbors
```