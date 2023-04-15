from numpy import *


def ray_line_intersection(rd, a, dpt):
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
    d = dc[0] * ba[1] - ba[1] * dc[0] # cross(DC, AB)

    # Handle the hopefully rare parallel case where they may overlap
    if (d == 0) and handle_parallel:
        # This is basically construcing an inverse matrix from ba,
        # and checking if the intervals overlap.
        # First test if the CD is on the same plane as AB
        norm = 1.0 / dot(ba, ba)
        r0 = array(ba[1], ba[0]) * norm
        ix = dot(c - a, r0)
        if abs(ix) > 1e-7:
            return -1

        # Compute their intevals
        r1 = array(-r0[1], r0[0])
        i0 = dot(c - a, r1)
        i1 = dot(c - a + dc, r1)

        tmin = min(i0, i1)
        tmax = max(i0, i1)

        if (tmax < 0) or (tmin > 1):
            return -1
        # Interval chosen will be closest to A
        return tmin

    sign_d = sign(d)
    u = (ac[0] * ba[1] - ac[1] * ba[0]) * sign_d # cross(AC, BA) * sign(d)
    t = (ac[0] * dc[1] - ac[1] * dc[0]) * sign_d # cross(AC, DC) * sign(d)
    if (min(u, t) > 0) and (max(u, t) >= abs(d)):
        return t / abs(d)
    return -1


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



class Vertex(object):
    def __init__(self, pos=None):
        self.pos = pos
        self.parent = None
        self.child = None

    def pop(self):
        self.parent.child = self.child
        self.child.parent = self.parent

    def insert_intersection_replacement(self, insert_a, insert_b):
        """Insert an intersection replacement.
        
        In order to handle if left/right rays and A->B intersect the same
        line segment
        
        We patch:
          self.parent.parent = self
          self.parent        = insert_a
          self               = insert_b
        
        This allows subsequent insertion logic to target the same vertex
        by reference, without needing to do messy correction logic.

        Args:
            insert_a (array[float]): First vertex to insert after this.
            insert_b (array[float]): Second vertex to insert after this.
        """
        grandparent = Vertex(self.pos)
        parent = Vertex(insert_a)
        self.pos = insert_b
        grandparent.parent = self.parent
        grandparent.child = parent
        parent.parent = grandparent
        parent.child = self
        self.parent = parent



class VisibilityPolygon(object):

    def __init__(self, triangle_scale=2):

        # Initialise with a triangle
        a = Vertex(array((-3 * triangle_scale, 0 * triangle_scale)))
        b = Vertex(array((1 * triangle_scale, 2 * triangle_scale)))
        c = Vertex(array((1 * triangle_scale, -2 * triangle_scale)))
            
        a.parent = c
        a.child = b

        b.parent = a
        b.child = c

        c.parent = b
        c.child = a

        self.head = a

    def add_line(self, line):
        x0, y0, x1, y1 = line            
        
        # Ensure clockwise orientation
        if (x1 * y0 - x0 * y1) < 0:
            x0, y0, x1, y1 = x1, y1, x0, y0

        a = array((x0, y0))
        b = array((x1, y1))
        dba = b - a
        
        first_vert = self.head
        current_vert = first_vert

        found_left_intersection = None
        found_middle_intersections = []
        found_right_intersection = None

        # Find all relevant intersections before actually doing any insertion logic
        while True:
            next_vert = current_vert.child

            curr_pt = current_vert.pos
            next_pt = next_vert.pos
            dpt = next_pt - curr_pt

            left_intersection = ray_line_intersection(a, curr_pt, dpt)
            right_intersection = ray_line_intersection(b, curr_pt, dpt)
            middle_intersection = line_line_intersection(a, dba, curr_pt, dpt, True)

            # Only ever keep the nearest left and right ray intersections
            if (left_intersection >= 0) and (left_intersection <= 1):
                pos = curr_pt + dpt * left_intersection
                if not found_left_intersection:
                    found_left_intersection = (current_vert, pos)
                elif dot(pos, pos) < dot(found_left_intersection[1], found_left_intersection[1]):
                    found_left_intersection = (current_vert, pos)

            if (right_intersection >= 0) and (right_intersection <= 1):
                pos = curr_pt + dpt * right_intersection
                if not found_right_intersection:
                    found_right_intersection = (current_vert, pos)
                elif dot(pos, pos) < dot(found_right_intersection[1], found_right_intersection[1]):
                    found_right_intersection = (current_vert, pos)

            # However intersections between A and B need to be handled sequentially
            if (middle_intersection >= 0) and (middle_intersection <= 1):
                pos = curr_pt + dpt * middle_intersection
                found_middle_intersections.append((current_vert, pos))

            current_vert = next_vert
            if current_vert == first_vert:
                break

        # Pop nodes up until the first middle or right intersection
        # if found_left_intersection:
        #     src_anchor = found_left_intersection[0]
        #     dst_anchor = None
        #     if found_middle_intersections:
        #         dst_anchor = found_middle_intersections[0][0]
        #     elif found_right_intersection:
        #         dst_anchor = found_right_intersection[0]
        #     if dst_anchor and src_anchor != dst_anchor:
        #         while src_anchor.child != dst_anchor:
        #             src_anchor.child.pop()

        # # Pop end of middle to the right intersection
        # if found_middle_intersections and found_right_intersection:
        #     src_anchor = found_middle_intersections[-1][0]
        #     dst_anchor = found_right_intersection[0]
        #     if dst_anchor and src_anchor != dst_anchor:
        #         while src_anchor.child != dst_anchor:
        #             src_anchor.child.pop()

        if found_left_intersection:
            anchor, pos = found_left_intersection
            anchor.insert_intersection_replacement(pos, A)


        if found_right_intersection:
            anchor, pos = found_right_intersection
            anchor.insert_intersection_replacement(B, pos)



