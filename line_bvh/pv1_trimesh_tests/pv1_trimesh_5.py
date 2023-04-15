from numpy import *

def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]

def ray_line_intersection_ro0(rd, a, dpt):
    """Calculate the ray line intersection where Ro=(0, 0).

    Args:
        rd (array[float]): Ray direction
        a (array[float]): Line point A
        dpt (array[float]): B - A

    Returns:
        float: Intersection interval (t) : (a + dpt * t) = intersection point.
               (only valid if 0 <= t <= 1)
    """
    # https://www.geogebra.org/calculator/dug27m5r
    denom = dpt[0] * rd[1] - dpt[1] * rd[0] # cross(B - A, rd)
    if denom > 0:
        # cross(rd, a) / denom
        return (rd[0] * a[1] - rd[1] * a[0]) / denom
    return -1


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
    return ray_line_intersection_ro0(rd, a - rd, dpt)


def line_line_intersection(a, ba, c, dc, handle_parallel=False):
    """Calculate the intersection between two lines.

    Args:
        a (array[float]): Line point A
        ba (array[float]): B - A
        c (array[float]): Line point C
        dc (array[float]): D - C
        handle_parallel (bool): Handle parallel overlaps (Default: False).

    Returns:
        float: Intersection interval (t) : (a + ba * t) = intersection point.
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


def ccw_weight(dab, dcb):
    numerator = dab[0] * dcb[1] - dab[1] * dcb[0]
    denom = dot(dab, dcb)
    return pi - arctan2(-numerator, -denom)


def colinear_rays(a, b):
  """Check if two rays are approximately colinear.

  Args:
    a (array[float]): First ray direction
    b (array[float]): Second ray direction

  Returns:
    bool: True if colinear.
  """
  return (dot(a, b)) > 0 and (abs(cross(a, b)) <= 1e-5)



r"""

Graph Based Polygon Subtraction


We start with a base polygon which represents the current visibility span,
orientated clockwise:

 A---------------------------->B
  ^                           /
   \                         /
    \                       /
     \                     /
      \                   /
       \                 /
        \               /
         \             /
          \           /
           \         /
            \       /
             \     /
              \   /
               \ v
                C


We then project the line and calculate intersection points:


 A-----------------X---------->B
  ^               /           /
   \             /           /
    \           L0          /
     \            \        /
      \           L1------X
       \                 /
        \               /
         \             /
          \           /
           \         /
            \       /
             \     /
              \   /
               \ v
                C


We then follow the graph, proceeding in the most clockwise direction, until
# we hit a previously seen point.

 A---------------->B
  ^               /
   \             V
    \            C
     \            \
      \            D----->E
       \                 /
        \               /
         \             /
          \           /
           \         /
            \       /
             \     /
              \   /
               \ v
                F
"""

# There can only reasonably be an even number of intersections?
# If RayA and RayB could only ever intesect once.


class Vertex(object):

  def __init__(self, pos):
    self.pos = pos
    self.child = None

  def swap_child(self, new_child):
    old_child = self.child
    self.child = new_child
    return old_child



class VisibilityPolygon(object):

    def __init__(self, triangle_scale=2):
        # Init with a triangle
        a = Vertex(array((-3.0 * triangle_scale, 0.0 * triangle_scale)))
        b = Vertex(array((1.0 * triangle_scale, 2.0 * triangle_scale)))
        c = Vertex(array((1.0 * triangle_scale, -2.0 * triangle_scale)))            
        a.child = b
        b.child = c
        c.child = a
        self.head = a

    def get_vertices(self):
        it = self.head
        while True:
            yield it
            it = it.child
            if it == self.head:
                break


    def _add_ab_intersections(self, a, dba):

        intervals = []

        current_vertex = self.head
        while True:
            pta = current_vertex.pos
            dpt = current_vertex.child.pos - pta
            t = line_line_intersection(a, dba, pta, dpt)
            
            if t >= 0 and t <= 1:
                intervals.append((t, current_vertex))

            current_vertex = current_vertex.child
            if current_vertex == self.head:
                break

        ## .......... hrm ............ ????
        if intervals:
            intervals.sort()
            inside = False
            for t, vertex in intervals:
                pos = a + dba * t
                new_vertex = Vertex(pos)
                if not inside:

                    inside = False
                else:

                    inside = True



    def add_line(self, line):
        x0, y0, x1, y1 = line

        # Ensure clockwise orientation
        if (x1 * y0 - x0 * y1) < 0:
            x0, y0, x1, y1 = x1, y1, x0, y0

        a = array((x0, y0))
        b = array((x1, y1))

        if colinear_rays(a, b):
            return

        dba = b - a

        self._add_ab_intersections(a, dba)

        # Scan for where RayA and RayB intersect
        found_intersection_a = None
        found_intersection_b = None

        current_vertex = self.head

        while True:
            pta = current_vertex.pos
            dpt = current_vertex.child.pos - pta

            intersect_a = ray_line_intersection(a, pta, dpt)
            if intersect_a >= 0 and intersect_a <= 1:
                pos = pta + dpt * intersect_a
                if not found_intersection_a or dot(pos, pos) < dot(found_intersection_a[1], found_intersection_a[1]):
                    found_intersection_a = (current_vertex, pos)

            intersect_b = ray_line_intersection(b, pta, dpt)
            if intersect_b >= 0 and intersect_b <= 1:
                pos = pta + dpt * intersect_b
                if not found_intersection_b or dot(pos, pos) < dot(found_intersection_b[1], found_intersection_b[1]):
                    found_intersection_b = (current_vertex, pos)

            current_vertex = current_vertex.child
            if current_vertex == self.head:
                break

        # If both RayA and RayB intersect geometry, then our polygon will
        # now follow this pattern:
        # Input->IA->A-> ... other A->B intersections ... ->B->IB->Output
        if found_intersection_a and found_intersection_b:

            in_vertex = found_intersection_a[0]
            ia_vertex = Vertex(found_intersection_a[1])
            a_vertex = Vertex(a)
            b_vertex = Vertex(b)
            ib_vertex = Vertex(found_intersection_b[1])
            out_vertex = found_intersection_b[0].child
            self.head = in_vertex

            clipped_start = in_vertex.child

            in_vertex.child = ia_vertex
            ia_vertex.child = a_vertex
            a_vertex.child = b_vertex
            b_vertex.child = ib_vertex
            ib_vertex.child = out_vertex

            # If RayA and RayB intersect the same line, then A->B cannot intersect
            # any other edge.
            if found_intersection_a[0] == found_intersection_b[0]:
                return

            # Detect any intersections between A->B and the edges
            # we've just clipped.
            prev_vertex = a_vertex
            inside = False
            it = clipped_start
            while it != out_vertex:
                pta = it.pos
                dpt = it.child.pos - pta
                t = line_line_intersection(a, dba, pta, dpt)
                # Intersection, but repurpose the vertex
                if t >= 0 and t <= 1:
                    pos = a + dba * t
                    if not inside:
                        it.pos = pos
                        prev_vertex.child = it
                        inside = True
                    else:
                        cloned_it = Vertex(it.pos)
                        cloned_it.child = it.child

                        new_child = Vertex(pos)
                        it.child = new_child
                        prev_vertex = new_child
                        it = cloned_it

                        inside = False
                it = it.child

            prev_vertex.child = b_vertex



if __name__ == "__main__":
    p = VisibilityPolygon()
    p.add_line(array((0.3320395938842,0.2892271257039, 0.2115759855531,0.626525229031)))
    p.add_line(array((-0.4760480959557,0.1311095656039, -0.3162727175992,0.7121109414457)))
    p.add_line(array((-0.2916018517206,0.3199053271587, 0.1102143253821,0.2009405687849)))
    p.add_line(array((-0.7731100796368,0.1230241779685, 0.2421012862217,0.3098906668697)))
    print("{{{0}}}".format(
        ",".join(
            "vector(({0[0]},{0[1]}),({1[0]},{1[1]}))".format(v.pos, v.child.pos)
            # "vertex(({0},{1}))".format(v.pos, v.child.pos)
            for v in p.get_vertices()
        )
    ))
