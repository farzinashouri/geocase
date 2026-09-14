def geohash_neighbors(gh):
    """Return geohashes of 8 surrounding cells at same precision."""
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    
    def decode_bounds(geohash):
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        is_lon = True
        for char in geohash:
            idx = BASE32.index(char)
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
        return lat_range, lon_range
    
    def encode_geohash(lat, lon, precision):
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        is_lon = True
        bits = 0
        bit = 0
        result = []
        lon = ((lon + 180) % 360) - 180
        while len(result) < precision:
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon > mid:
                    bits |= (1 << (4 - bit))
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat > mid:
                    bits |= (1 << (4 - bit))
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_lon = not is_lon
            bit += 1
            if bit == 5:
                result.append(BASE32[bits])
                bits = 0
                bit = 0
        return ''.join(result)
    
    lat_range, lon_range = decode_bounds(gh)
    lat_center = (lat_range[0] + lat_range[1]) / 2
    lon_center = (lon_range[0] + lon_range[1]) / 2
    lat_height = lat_range[1] - lat_range[0]
    lon_width = lon_range[1] - lon_range[0]
    
    neighbors = []
    for dlat in [-1, 0, 1]:
        for dlon in [-1, 0, 1]:
            if dlat == 0 and dlon == 0:
                continue
            new_lat = lat_center + dlat * lat_height
            new_lon = lon_center + dlon * lon_width
            if new_lat > 90 or new_lat < -90:
                continue
            neighbors.append(encode_geohash(new_lat, new_lon, len(gh)))
    return neighbors