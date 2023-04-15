"""
Simple Line BVH
---------------

Each entry contains the following structure:

    struct Node
    {
        float4 v0;  // metadata0, metadata1
        float4 v1;  // bbox0 or line0
        float4 v2;  // bbox1 or line1
    };


Which is split via:
    struct Entry
    {
        float2 metadata;    // (asuint) .x = 0 if bbox
                            //               1 if line
                            //
                            // (asuint) .y = Next node float4 address if bbox.
                            //               Line id if line.

        float4 data;        // (bbox) .xy = bbox min, .zw = bbox max
                            // (line) .xy = float2(x0, y0), .zw = float2(x0-x1, y0-y1)
    };


    Entry A = {node.v0.xy, node.v1};
    Entry B = {node.v0.zw, node.v2};

If there is only one leaf, it is guaranteed to be in A, to make
subsequent distance tests simpler, in a shader.
"""

from numpy import *


NODE_FLOAT4_STRIDE = 3

# Must match the output of make_line_entries
IDX_CENTER_X = 0
IDX_CENTER_Y = 1
IDX_X0 = 2
IDX_Y0 = 3
IDX_DX = 4
IDX_DY = 5
IDX_ID = 6

METADATA_BBOX = uint32(0).view(float32)
METADATA_LINE = uint32(1).view(float32)

# Must match make_bvh_iter
BVH_IDX_METADATA = 0
BVH_IDX_ENTRY_ID = 1
BVH_IDX_DATA = 2
BVH_IDX_BBOX = 3
BVH_IDX_EXTRA_DATA = 4


class AddressAllocator(object):
    """Encapsulates allocation of nodes within the final structure."""

    def __init__(self):
        self._address = 0

    def alloc(self):
        value = self._address
        self._address += NODE_FLOAT4_STRIDE
        return value

    def get_allocation_size(self):
        return self._address


def make_line_entries(lines):
    """Makes line entries in a uniform structure, to make numpy work easier.

    Args:
        lines (array[float[4]]): Lines to build a bvh from.

    Returns:
        array[float[7]]: Structured line entries.
    """
    x0 = lines[:, 0]
    y0 = lines[:, 1]
    x1 = lines[:, 2]
    y1 = lines[:, 3]
    dx = x0 - x1
    dy = y0 - y1
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    ids = arange(len(lines), dtype=uint32).view(float32)

    # It's just generally a lot easier to do the math via numpy
    # by creating an array with a structure like this.

    # TODO: Should probably filter out duplicates...

    return array(
        [
            cx, # 0 (IDX_CENTER_X)
            cy, # 1 (IDX_CENTER_Y)
            x0, # 2 (IDX_X0)
            y0, # 3 (IDX_Y0)
            dx, # 4 (IDX_DX)
            dy, # 5 (IDX_DY)
            ids # 6 (IDX_ID)
        ],
        dtype = float32
    ).T



def make_bvh_iter(entries, allocator, fast_build=True, sorted_dim=-1):
    """Iterator for building BVH entries.

    Args:
        entries (array(float[7])): Structured line entries.
        allocator (AddressAllocator): Allocator for requesting a new address.
        fast_build (bool): Use a faster build method. (Default: True)
        sorted_dim (int): Axis data is sorted. (Default: -1)

    Returns:
        tuple: metadata, entry_id, data, bbox, extra_data
    """

    assert len(entries) != 0

    # Generate a leaf, no extra allocation needed
    if len(entries) == 1:
        entry = entries[0]
        x0 = entry[IDX_X0]
        y0 = entry[IDX_Y0]
        x1 = x0 - entry[IDX_DX]
        y1 = y0 - entry[IDX_DY]
        return (
            METADATA_LINE,                                          # BVH_IDX_METADATA
            entry[IDX_ID],                                          # BVH_IDX_ENTRY_ID
            entry[IDX_X0:IDX_DY+1],                                 # BVH_IDX_DATA
            (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)),   # BVH_IDX_BBOX
            (),                                                     # BVH_IDX_EXTRA_DATA
        )

    allocated_index = allocator.alloc()

    # No need to sort anything when we're on our final node
    if len(entries) > 2:
        min_cx = min(entries[:, IDX_CENTER_X])
        min_cy = min(entries[:, IDX_CENTER_Y])
        max_cx = max(entries[:, IDX_CENTER_X])
        max_cy = max(entries[:, IDX_CENTER_Y])
        if (max_cx - min_cx) > (max_cy - min_cy):
            if sorted_dim != 0:
                sorted_dim = 0
                entries[:] = entries[argsort(entries[:, IDX_CENTER_X])]
        elif sorted_dim != 1:
            sorted_dim = 1
            entries[:] = entries[argsort(entries[:, IDX_CENTER_Y])]

    # Split into left and right parts, if we have an odd number, put the
    # center line into which ever half has a closer mean cx, cy.
    #
    # If we're opting for a fast build, appoximate a center using:
    #   (entries[0], entries[split_index-1])
    #   and
    #   (entries[split_index+1], entries[-1])
    split_index = len(entries) // 2

    if (len(entries) & 1) == 1:
        if fast_build:
            left_cx = (entries[0, IDX_CENTER_X] + entries[split_index-1, IDX_CENTER_X]) * 0.5
            left_cy = (entries[0, IDX_CENTER_Y] + entries[split_index-1, IDX_CENTER_Y]) * 0.5
            right_cx = (entries[split_index+1, IDX_CENTER_X] + entries[-1, IDX_CENTER_X]) * 0.5
            right_cy = (entries[split_index+1, IDX_CENTER_Y] + entries[-1, IDX_CENTER_Y]) * 0.5
        else:
            left_cx = mean(entries[0:split_index, IDX_CENTER_X])
            left_cy = mean(entries[0:split_index, IDX_CENTER_Y])
            right_cx = mean(entries[(split_index+1):, IDX_CENTER_X])
            right_cy = mean(entries[(split_index+1):, IDX_CENTER_Y])

        mid_cx = entries[split_index, IDX_CENTER_X]
        mid_cy = entries[split_index, IDX_CENTER_Y]

        left_dist_sq = dot(
            (left_cx - mid_cx, left_cy - mid_cy),
            (left_cx - mid_cx, left_cy - mid_cy)
        )
        right_dist_sq = dot(
            (right_cx - mid_cx, right_cy - mid_cy),
            (right_cx - mid_cx, right_cy - mid_cy)
        )
        if left_dist_sq < right_dist_sq:
            split_index += 1

    left = make_bvh_iter(entries[:split_index], allocator, fast_build, sorted_dim)
    right = make_bvh_iter(entries[split_index:], allocator, fast_build, sorted_dim)

    linear_extra_data_first = left[BVH_IDX_EXTRA_DATA]
    linear_extra_data_second = right[BVH_IDX_EXTRA_DATA]

    # Ensure first entry is always a line
    if (right[BVH_IDX_METADATA] == METADATA_LINE) and (left[BVH_IDX_METADATA] != METADATA_LINE):
        left, right = right, left

    bbox = (
        min(left[BVH_IDX_BBOX][0], right[BVH_IDX_BBOX][0]),
        min(left[BVH_IDX_BBOX][1], right[BVH_IDX_BBOX][1]),
        max(left[BVH_IDX_BBOX][2], right[BVH_IDX_BBOX][2]),
        max(left[BVH_IDX_BBOX][3], right[BVH_IDX_BBOX][3]),
    )

    extra_data = array(
        [
            # v0
            left[BVH_IDX_METADATA], left[BVH_IDX_ENTRY_ID], right[BVH_IDX_METADATA], right[BVH_IDX_ENTRY_ID],
            # v1
            left[BVH_IDX_DATA][0], left[BVH_IDX_DATA][1], left[BVH_IDX_DATA][2], left[BVH_IDX_DATA][3],
            # v2
            right[BVH_IDX_DATA][0], right[BVH_IDX_DATA][1], right[BVH_IDX_DATA][2], right[BVH_IDX_DATA][3],
        ],
        dtype=float32
    )

    # len needed in case of numpy array, which will throw an error
    if len(linear_extra_data_first):
        extra_data = append(extra_data, linear_extra_data_first)
    if len(linear_extra_data_second):
        extra_data = append(extra_data, linear_extra_data_second)

    return (
        METADATA_BBOX,                          # BVH_IDX_METADATA
        uint32(allocated_index).view(float32),  # BVH_IDX_ENTRY_ID
        bbox,                                   # BVH_IDX_DATA
        bbox,                                   # BVH_IDX_BBOX
        extra_data,                             # BVH_IDX_EXTRA_DATA
    )


def build_line_bvh_v1(lines, fast_build=True):

    if not len(lines):
        return None

    allocator = AddressAllocator()
    entries = make_line_entries(lines)

    # We need atleast 2 entries to ensure a root node
    # gets allocated, so in which case, we just duplicate
    # the single line.
    if len(entries) == 1:
        entries = stack((entries[0], entries[0]))

    result = make_bvh_iter(entries, allocator, fast_build)
    return result[BVH_IDX_EXTRA_DATA].reshape(
        (len(result[BVH_IDX_EXTRA_DATA])//4, 4)
    )


# For WEBGL stuff, this should be done using WASM

class LineBvhV1Result(object):

     def __init__(self):
        self.hit_line_id = 0xffffffff
        self.hit_dist_sq = 0
        self.line = (0, 0, 0, 0)
        self.hit_line_interval = 0
        self.duv = array((0, 0)) # ro + dUV = intersection point


def line_bvh_v1_eval_entry(ro, inv_rd, metadata, data, result):
    """Helper function to evaluate a BVH entry.

    Args:
        ro (float2): Ray origin.
        inv_rd (float2): Inverse ray direction.
        metadata (float2): BVH metadata.
        data (float4): BVH entry data.
        result (LineBvhV1Result): Writeback.

    Returns:
        tuple: (add to stack, bbox hit distance, id to add)
    """
    if metadata[0] == METADATA_LINE:
        A = ro
        AB = -result.duv
        C = data[0:2]
        CD = data[2:4]
        AC = A - C

        d = AB[0] * CD[1] - AB[1] * CD[0] # cross(AB, CD)
        u = AC[0] * AB[1] - AC[1] * AB[0] # cross(AC, AB)
        v = AC[0] * CD[1] - AC[1] * CD[0] # cross(AC, CD)

        dsign = sign(d)
        u *= dsign
        v *= dsign

        if (min(u, v) > 0.0) and (max(u, v) < abs(d)):
            result.hit_line_id = metadata[1].view(uint32)
            result.hit_line_interval = -u / abs(d)
            result.line = data
            result.duv *= v / abs(d)
            result.hit_dist_sq = (
                result.duv[0] * result.duv[0]
                + result.duv[1] * result.duv[1]
            )

    # metadata[0] == METADATA_BBOX
    else:
        bbox_min = data[0:2]
        bbox_max = data[2:4]
        xintervals = ((bbox_min[0] - ro[0]) * inv_rd[0], (bbox_max[0] - ro[0]) * inv_rd[0])
        yintervals = ((bbox_min[1] - ro[1]) * inv_rd[1], (bbox_max[1] - ro[1]) * inv_rd[1])
        if xintervals[0] > xintervals[1]:
            xintervals = (xintervals[1], xintervals[0])
        if yintervals[0] > yintervals[1]:
            yintervals = (yintervals[1], yintervals[0])
        intervals = (
            max(0, max(xintervals[0], yintervals[0])),
            min(xintervals[1], yintervals[1])
        )

        if (
                (intervals[0] < intervals[1])
                and ((intervals[0] * intervals[0]) < result.hit_dist_sq)
        ):
            return (
                True,
                intervals[0],
                metadata[1].view(uint32)
            )

    return (False, 0, 0)


# In C++ if we use it, template stop on first hit etc
# really the GLSL version is a better reference
def trace_line_bvh_v1(bvh_data, ro, rd, max_dist, stop_on_first_hit):
    """Line trace a bvh.

    Args:
        bvh_data (numpy.array[float4]): BVH structure.
        ro (float2): Ray direction
        rd (float2): Ray origin
        max_dist (float): Max distance to trace
        stop_on_first_hit (bool): Whether or not to stop on the first hit

    Returns:
        LineBvhV1Result: Result.
    """

    ro = array(ro)
    rd = array(rd)

    result = LineBvhV1Result()
    result.hit_dist_sq = max_dist * max_dist
    result.duv = rd * max_dist

    head = 0
    stack = []

    inv_rd = 1.0 / rd

    while True:
        v0 = bvh_data[head]
        left_meta = v0[0:2]
        left_data = bvh_data[head + 1]
        right_meta = v0[2:4]
        right_data = bvh_data[head + 2]

        left_add_to_stack, left_dist, left_id = line_bvh_v1_eval_entry(
            ro,
            inv_rd,
            left_meta,
            left_data,
            result
        )

        right_add_to_stack, right_dist, right_id = line_bvh_v1_eval_entry(
            ro,
            inv_rd,
            right_meta,
            right_data,
            result
        )

        if stop_on_first_hit:
            if result.hit_line_id != 0xffffffff:
                break

        # Prioritise nearest
        if left_add_to_stack and right_add_to_stack:
            if left_dist < right_dist:
                left_id, right_id = right_id, left_id
            stack.append(left_id)
            head = right_id
        elif left_add_to_stack:
            head = left_id
        elif right_add_to_stack:
            head = right_id
        elif stack:
            head = stack.pop()
        else:
            break

    return result
