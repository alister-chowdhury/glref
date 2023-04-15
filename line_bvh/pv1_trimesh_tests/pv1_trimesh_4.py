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



def ccw_weight(dab, dcb):
    numerator = dab[0] * dcb[1] - dab[1] * dcb[0]
    denom = dot(dab, dcb)
    return pi - arctan2(-numerator, -denom)

class Vertex(object):
    def __init__(self, pos=None):
        self.pos = pos
        self.parent = None
        self.child = None

    def pop(self):
        self.parent.child = self.child
        self.child.parent = self.parent

    def insert_after(self, new_pos):
        new_vertex = Vertex(new_pos)
        new_vertex.parent = self
        new_vertex.child = self.child
        self.child.parent = new_vertex
        self.child = new_vertex
        return new_vertex

    def insert_before(self, new_pos):
        new_vertex = Vertex(new_pos)
        new_vertex.parent = self.parent
        new_vertex.child = self
        self.parent.child = new_vertex
        self.parent = new_vertex
        return new_vertex


class VisibilityPolygon(object):

    def __init__(self, triangle_scale=2):

        # Initialise with a triangle
        a = Vertex(array((-3.0 * triangle_scale, 0.0 * triangle_scale)))
        b = Vertex(array((1.0 * triangle_scale, 2.0 * triangle_scale)))
        c = Vertex(array((1.0 * triangle_scale, -2.0 * triangle_scale)))
            
        a.child = b
        b.child = c
        c.child = a

        a.parent = c
        b.parent = a
        c.parent = b

        self.head = a


    def add_line(self, line, cleanup=True):
        x0, y0, x1, y1 = line            
        
        # Ensure clockwise orientation
        if (x1 * y0 - x0 * y1) < 0:
            x0, y0, x1, y1 = x1, y1, x0, y0

        a = array((x0, y0))
        b = array((x1, y1))
        dba = b - a



if __name__ == "__main__":
    p = VisibilityPolygon()
    # p.add_line(array((0.3320395938842,0.2892271257039, 0.2115759855531,0.626525229031)))
    # p.add_line(array((-0.4760480959557,0.1311095656039, -0.3162727175992,0.7121109414457)), )
    # p._debug_print_connections()