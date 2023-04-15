from numpy import *
from itertools import chain
import bisect

# No good cus needs prefragmentation and broken logic


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def closest_point_to_line(a, b):
    # https://www.geogebra.org/calculator/aajzrdep
    ab = a - b
    t = max(0.0, min(1.0, dot(a, ab) / dot(ab, ab)))
    return a - ab * t


def ray_line_intersection(rd, a, dpt):
    """Calculate the ray line intersection where Ro=Rd.

    Args:
        rd (array[float]): Ray direction
        a (array[float]): Line point A
        dpt (array[float]): B - A

    Returns:
        float: Intersection interval (t) : (a + dpt * t) = intersection point.
               (only valid if 0 <= t <= 1)
    """
    a = a - rd
    denom = cross(dpt, rd)
    if denom > 0:
        return cross(rd, a) / denom
    return -1


def line_line_intersection(a, ba, c, dc, handle_parallel=False):
    """Calculate the intersection between two lines.

    Args:
        a (array[float]): Line point A
        ba (array[float]): B - A
        c (array[float]): Line point C
        dc (array[float]): D - C
        handle_parallel (bool): Handle parallel overlaps (Default: False).

    Returns:
        float: Intersection interval (t) : (c + dc * t) = intersection point.
               (only valid if 0 <= t <= 1)
    """
    # https://www.geogebra.org/calculator/ytnhzgzb
    ac = a - c
    d = cross(dc, ba)

    # Handle the hopefully rare parallel case where they may overlap
    if (d == 0) and handle_parallel:
        # This is basically construcing an inverse matrix from ba,
        # and checking if the intervals overlap.
        # First test if the CD is on the same plane as AB
        norm = 1.0 / dot(ba, ba)
        r0 = array((ba[1], ba[0])) * norm
        ix = dot(c - a, r0)
        if abs(ix) > 1e-7:
            return -1

        # Compute their intevals
        r1 = array((-r0[1], r0[0]))
        i0 = dot(c - a, r1)
        i1 = dot(c - a + dc, r1)

        tmin = min(i0, i1)
        tmax = max(i0, i1)

        if (tmax < 0) or (tmin > 1):
            return -1
        # Interval chosen will be closest to A
        return tmin

    sign_d = sign(d)
    u = cross(ac, ba) * sign_d
    t = cross(ac, dc) * sign_d
    if (min(u, t) >= 0) and (max(u, t) <= abs(d)):
        return t / abs(d)
    return -1



class DistanceOrderedLines(object):

    def __init__(self):
        self._entries = []
        self._seen = set()

    @staticmethod
    def sorted_p(a, b):
        if a[0] < b[0] or (a[0] == b[0] and a[1] < b[1]):
            a, b = b, a
        return a, b

    def add(self, a, b, distsq):
        a, b = self.sorted_p(a, b)
        h = hash((a.tobytes(), b.tobytes()))
        if h in self._seen:
            return
        self._seen.add(h)
        key = (distsq, (a[0], a[1], b[0], b[1]), h)
        bisect.insort(self._entries, key)

    def head_distsq(self):
        return self._entries[0][0]

    def head_line(self):
        x0, y0, x1, y1 = self._entries[0][1]
        return array((x0, y0)), array((x1, y1))

    def remove(self, a, b):
        a, b = self.sorted_p(a, b)
        h = hash((a.tobytes(), b.tobytes()))
        self._seen.remove(h)
        i = 0
        while i < len(self._entries):
            if self._entries[i][2] == h:
                self._entries.pop(i)
                break
            i += 1

    def empty(self):
        return len(self._entries) == 0





# End is 0 so when sorting occurs it's picked up first
EVENT_END_VERTEX = 0
EVENT_START_VERTEX = 1


def calculate_visibility_hull(point, lines):

    # Based off:
    # https://github.com/trylock/visibility/

    diststate = DistanceOrderedLines()
    events = []


    bbox = array((
        (0.0, 0.0, 0.0, 1.0),
        (0.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 0.0),
        (1.0, 0.0, 0.0, 0.0),
    ))

    for line in chain.from_iterable((lines, bbox)):
        x0, y0, x1, y1 = line

        # Keep the lines relative to the point, this makes other
        # logic a bit simpler
        a = array((x0, y0)) - point
        b = array((x1, y1)) - point
        
        # Ensure consistent winding
        d = cross(a, b)

        # Skip colinear lines
        if abs(d) <= 1e-9:
            continue

        if d > 0:
            b, a = a, b

        closest_point = closest_point_to_line(a, b)
        distsq = dot(closest_point, closest_point)

        a_w = arctan2(-a[0], -a[1])
        b_w = arctan2(-b[0], -b[1])

        events.append((a_w, EVENT_START_VERTEX, a, b, distsq))
        events.append((b_w, EVENT_END_VERTEX, b, a, distsq))

        # Init diststate with boundary crossing lines
        if a_w > b_w:
            diststate.add(a, b, distsq)

    events.sort()

    verts = []

    for _, event_type, a, b, distsq in events:
        if event_type == EVENT_END_VERTEX:
            diststate.remove(a, b)

        if diststate.empty():
            verts.append(a)

        # Compute new nearest line segment intersection
        elif distsq < diststate.head_distsq():
            cmp_a, cmp_b = diststate.head_line()
            d_cmpba = cmp_b - cmp_a
            t = line_line_intersection(a, b-a, cmp_a, d_cmpba)

            # Shouldn't be possible, for there to be no intersection
            # but just incase, we'll just assume it's because of a degenerate
            # point.
            # print(cmp_a, cmp_b, a, b)
            if t <= 0 or t >= 1:
                verts.append(a)
            else:
                intersection = cmp_a + d_cmpba * t
                if event_type == EVENT_START_VERTEX:
                    verts.append(intersection)
                    verts.append(a)
                else: # EVENT_END_VERTEX
                    verts.append(a)
                    verts.append(intersection)

        if event_type == EVENT_START_VERTEX:
            diststate.add(a, b, distsq)

    # print(verts)
    # print("{{{0}}}".format(
    #     ",".join(
    #         "({0},{1})".format(p[0], p[1])
    #         for p in verts
    #     )
    # ))
    print("{{{0}}}".format(
        ",".join(
            "vector(({0[0]},{0[1]}),({1[0]},{1[1]}))".format(verts[i-1], verts[i])
            for i in range(len(verts))
        )
    ))
    print("")
    print("{{{0}}}".format(
        ",".join(
            "vector(({0[0]},{0[1]}),({0[2]},{0[3]}))".format(line - (point[0], point[1], point[0], point[1]))
            for line in chain.from_iterable((lines, bbox))
        )
    ))



lines = array([
    (0.3320395938842,0.2892271257039, 0.2115759855531,0.626525229031),
    (-0.4760480959557,0.1311095656039, -0.3162727175992,0.7121109414457)
]) + 0.5


calculate_visibility_hull(array((0.5, 0.5)), lines)
