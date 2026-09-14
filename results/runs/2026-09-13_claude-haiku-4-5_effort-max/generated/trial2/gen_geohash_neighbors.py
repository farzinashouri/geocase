def geohash_neighbors(gh):
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def decode_bounds(gh):
        """Decode geohash to get lat/lon bounds"""
        lat_min, lat_max = -90.0, 90.0
        lon_min, lon_max = -180.0, 180.0
        is_lon = True
        
        for char in gh:
            idx = BASE32.index(char)
            for i in range(4, -1, -1):
                bit = (idx >> i) & 1
                if is_lon:
                    mid = (lon_min + lon_max) / 2
                    if bit == 1:
                        lon_min = mid
                    else:
                        lon_max = mid
                else:
                    mid = (lat_min + lat_max) / 2
                    if bit == 1:
                        lat_min = mid
                    else:
                        lat_max = mid
                is_lon = not is_lon
        
        return lat_min, lat_max, lon_min, lon_max
    
    def encode(lat, lon, precision):
        """Encode lat/lon to geohash"""
        lat_min, lat_max = -90.0, 90.0
        lon_min, lon_max = -180.0, 180.0
        geohash = []
        is_lon = True
        bits = 0
        bit_count = 0
        
        while len(geohash) < precision:
            if is_lon:
                mid = (lon_min + lon_max) / 2
                if lon >= mid:
                    bits = (bits << 1) | 1
                    lon_min = mid
                else:
                    bits = bits << 1
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2
                if lat >= mid:
                    bits = (bits << 1) | 1
                    lat_min = mid
                else:
                    bits = bits << 1
                    lat_max = mid
            
            is_lon = not is_lon
            bit_count += 1
            
            if bit_count == 5:
                geohash.append(BASE32[bits])
                bits = 0
                bit_count = 0
        
        return ''.join(geohash)
    
    lat_min, lat_max, lon_min, lon_max = decode_bounds(gh)
    lat_height = lat_max - lat_min
    lon_width = lon_max - lon_min
    precision = len(gh)
    
    neighbors = []
    for dlat in [-1, 0, 1]:
        for dlon in [-1, 0, 1]:
            if dlat == 0 and dlon == 0:
                continue
            
            new_lat = (lat_min + lat_max) / 2 + dlat * lat_height
            new_lon = (lon_min + lon_max) / 2 + dlon * lon_width
            
            if new_lon > 180:
                new_lon -= 360
            elif new_lon < -180:
                new_lon += 360
            
            neighbor_lat_min = new_lat - lat_height / 2
            neighbor_lat_max = new_lat + lat_height / 2
            
            if neighbor_lat_min < -90 or neighbor_lat_max > 90:
                continue
            
            neighbor_gh = encode(new_lat, new_lon, precision)
            neighbors.append(neighbor_gh)
    
    return neighbors