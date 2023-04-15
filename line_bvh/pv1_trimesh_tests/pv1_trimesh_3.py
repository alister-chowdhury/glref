from numpy import *


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]

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
        self.children = []


class VisibilityPolygon(object):

    def __init__(self, triangle_scale=2):

        # Initialise with a triangle
        a = Vertex(array((-3.0 * triangle_scale, 0.0 * triangle_scale)))
        b = Vertex(array((1.0 * triangle_scale, 2.0 * triangle_scale)))
        c = Vertex(array((1.0 * triangle_scale, -2.0 * triangle_scale)))
            
        a.children = [b]
        b.children = [c]
        c.children = [a]

        self.vertices = [a, b, c]

    def _debug_print_connections(self):
        all_nodes = set()
        to_process = set(self.vertices)
        while to_process:
            next_node = to_process.pop()
            if next_node in all_nodes:
                continue
            all_nodes.add(next_node)
            to_process.update(next_node.children)

        print("{{{0}}}".format(
            ",".join(
                "vector(({0},{1}),({2},{3}))".format(
                    cur.pos[0], cur.pos[1], child.pos[0], child.pos[1]
                )
                for cur in all_nodes
                for child in cur.children
            )
        ))


    def fixup_connections(self):
        
        # Possibly prone to errors?
        # Need this
        first = next(node for node in self.vertices if len(node.children) == 1)
        prev = first
        curr = prev.children[0]
        self.vertices = [prev]

        while curr != first:
            self.vertices.append(curr)
            next_best = curr.children[0]

            if len(curr.children) > 1:
                prev_pos = prev.pos
                curr_pos = curr.pos
                dir_a = prev_pos - curr_pos
                dir_b = curr.children[0].pos - curr_pos
                next_best_weight = ccw_weight(dir_a, dir_b)
                for child in curr.children[1:]:
                    dir_b = child.pos - curr_pos
                    weight = ccw_weight(dir_a, dir_b)
                    if weight > next_best_weight:
                        next_best = child
                        next_best_weight = weight
            
            prev = curr
            curr = next_best

        for i in range(len(self.vertices)):
            self.vertices[i-1].children = [self.vertices[i]]



    def add_line(self, line, cleanup=True):
        x0, y0, x1, y1 = line            
        
        # Ensure clockwise orientation
        if (x1 * y0 - x0 * y1) < 0:
            x0, y0, x1, y1 = x1, y1, x0, y0

        a = array((x0, y0))
        b = array((x1, y1))
        dba = b - a

        current_vert = self.vertices[-1]

        found_left_intersection = None
        found_middle_intersections = []
        found_right_intersection = None

        for next_vert in self.vertices:

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

        last_connected = None

        if found_left_intersection:
            anchor, pos = found_left_intersection
            new_node_first = Vertex(pos)
            new_node_second = Vertex(a)
            new_node_first.children.append(new_node_second)
            new_node_second.children.extend(anchor.children)
            anchor.children = [new_node_first]
            last_connected = new_node_second

        for anchor, pos in found_middle_intersections:
            new_node = Vertex(pos)
            new_node.children.extend(anchor.children)
            anchor.children.append(new_node)
            if last_connected:
                last_connected.children.append(new_node)
            last_connected = new_node

        if found_right_intersection:
            anchor, pos = found_right_intersection
            new_node_first = Vertex(b)
            new_node_second = Vertex(pos)
            new_node_first.children.append(new_node_second)
            new_node_second.children.extend(anchor.children)
            anchor.children.append(new_node_first)
            if last_connected:
                new_node_second.children.extend(last_connected.children)
                last_connected.children = [new_node_first]
            last_connected = new_node_second

        # We only need to cleanup if nodes were actually inserted
        if cleanup and last_connected:
            self.fixup_connections()


if __name__ == "__main__":
    p = VisibilityPolygon()
    p.add_line(array((0.3320395938842,0.2892271257039, 0.2115759855531,0.626525229031)))
    p.add_line(array((-0.4760480959557,0.1311095656039, -0.3162727175992,0.7121109414457)), )
    p._debug_print_connections()