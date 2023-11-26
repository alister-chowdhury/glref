_SUM = sum
from numpy import *
sum = _SUM

def build_line_df_hybrid_v1(
        lines,
        res=256,
        extra_capture_pixel_span=1):
    
    # conform lines to (x0, y0, dx, dy)
    lines = array(lines, dtype=float32)
    lines[:,2] = lines[:,0] - lines[:,2]
    lines[:,3] = lines[:,1] - lines[:,3]

    capture_pixel_span = (
        (0.5 + extra_capture_pixel_span)
        * (2**0.5)
        * (1.0 / min(255, res))
    )

    capture_pixel_span_sq = capture_pixel_span ** 2

    df_component = ones((res, res), dtype=float32)
    num_lines_component = zeros((res, res), dtype=uint32)
    initial_bucket_ids_component = zeros((res, res), dtype=uint32)
    initial_buckets_mapping = {}

    for x, y in ((x_, y_) for x_ in range(res) for y_ in range(res)):
        uv = array(((x + 0.5) / res, (y + 0.5) / res), dtype=float32)

        # https://www.geogebra.org/calculator/aajzrdep
        Ax = lines[:,0] - uv[0]
        Ay = lines[:,1] - uv[1]
        ABx = lines[:,2]
        ABy = lines[:,3]

        t = (Ax * ABx + Ay * ABy) / (ABx * ABx + ABy * ABy)
        t = maximum(minimum(t, 1), 0)

        nearest_point_x = Ax - ABx * t
        nearest_point_y = Ay - ABy * t
        nearest_dist_sq = (
            (nearest_point_x * nearest_point_x)
            + (nearest_point_y * nearest_point_y)
        )

        filtered = nearest_dist_sq <= capture_pixel_span_sq
        num_lines = sum(filtered)
        df_sq = min(nearest_dist_sq[~filtered])
        line_ids = tuple(where(filtered)[0])

        df_component[y,x] = df_sq ** 0.5
        num_lines_component[y,x] = num_lines
        if line_ids not in initial_buckets_mapping:
            initial_buckets_mapping[line_ids] = len(initial_buckets_mapping)
        initial_bucket_ids_component[y,x] = initial_buckets_mapping[line_ids]

    # Do a relatively simple compression pass so we can reuse already written lines
    compressed_stream = []
    compress_lookup = {}
    
    for (line_ids, bucket_index) in sorted(
            initial_buckets_mapping.items(),
            key=lambda x: -len(x[0])):
        
        if bucket_index not in compress_lookup:
            # todo, use rabin-karp
            n = len(compressed_stream) - len(line_ids)
            found = None
            for i in range(n):
                if tuple(compressed_stream[i:i+len(line_ids)]) == line_ids:
                    found = i
                    break
            if not found:
                found = len(compressed_stream)
                compressed_stream.extend(line_ids)
            compress_lookup[bucket_index] = found

    df_bits = (maximum(df_component - 1.0/res, 1.0/255.0) * 255).astype(uint32)
    num_lines_bits = (num_lines_component << 8)
    offset_bits = array([
        [
            compress_lookup[bucket_index] << 16
            for bucket_index in onedim
        ]
        for onedim in initial_bucket_ids_component
    ], dtype=uint32)

    df_texture = df_bits | num_lines_bits | offset_bits
    lines_buffer = lines[compressed_stream]

    return df_texture, lines_buffer
