```python
def geohash_neighbors(gh):
    base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    precision = len(gh)
    
    def decode_geohash(geohash):
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        is_lon = True
        
        for c in geohash:
            idx = base32.index(c)
            for i in range(4, -1, -1):
                bit = (idx >> i) & 1
                if is_lon:
                    mid = (lon_range[0] + lon_range[1]) / 2
                    if bit:
                        lon_range[0] = mid
                    else:
                        lon_range[1] = mid
                else:
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if bit:
                        lat_range[0] = mid
                    else:
                        lat_range[1] = mid
                is_lon = not is_lon
        
        return lat_range[0], lat_range[1], lon_range[0], lon_range[1]
    
    def encode_geohash(lat, lon, precision):
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        geohash = []
        bits = 0
        bit = 0
        ch = 0
        
        while len(geohash) < precision:
            if bits % 2 == 0:
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon > mid:
                    ch |= (1 << (4 - bit))
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat > mid:
                    ch |= (1 << (4 - bit))
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            
            bits += 1
            bit += 1
            
            if bit == 5:
                geohash.append(base32[ch])
                bit = 0
                ch = 0
        
        return ''.join(geohash)
    
    lat_min, lat_max, lon_min, lon_max = decode_geohash(gh)
    
    lat_height = lat_max - lat_min
    lon_width = lon_max - lon_min
    
    neighbors = []
    
    for dlat in [-1, 0, 1]:
        for dlon in [-1, 0, 1]:
            if dlat == 0 and dlon == 0:
                continue
            
            new_lon_min = lon_min + dlon * lon_width
            new_lon_max = lon_max + dlon * lon_width
            new_lat_min = lat_min + dlat * lat_height
            new_lat_max = lat_max + dlat * lat_height
            
            if new_lon_max > 180:
                new_lon_min = new_lon_min - 360
                new_lon_max = new_lon_max - 360
            elif new_lon_min < -180:
                new_lon_min = new_lon_min + 360
                new_lon_max = new_lon_max + 360
            
            if new_lat_max > 90 or new_lat_min < -90:
                continue
            
            neighbor_lat = (new_lat_min + new_lat_max) / 2
            neighbor_lon = (new_lon_min + new_lon_max) / 2
            neighbor_gh = encode_geohash(neighbor_lat, neighbor_lon, precision)
            neighbors.append(neighbor_gh)
    
    return neighbors
```