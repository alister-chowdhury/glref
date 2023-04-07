import os
from numpy import *
from numpy.linalg import norm

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders", "pointlights_v1")
)


GEN_PLANE_MAP_FRAG = os.path.join(_SHADER_DIR, "gen_plane_map.frag")
GEN_BBOX_FROM_PLANE_MAP_FRAG = os.path.join(_SHADER_DIR, "gen_bbox_from_plane_map.frag")
GEN_OBBOX_FROM_PLANE_MAP_FRAG = os.path.join(_SHADER_DIR, "gen_obbox_from_plane_map.frag")
DRAW_BBOX_VERT = os.path.join(_SHADER_DIR, "draw_bbox.vert")
DRAW_OBBOX_VERT = os.path.join(_SHADER_DIR, "draw_obbox.vert")
DRAW_BBOX_FRAG = os.path.join(_SHADER_DIR, "draw_bbox.frag")

DRAW_LIGHTS_VERT = os.path.join(_SHADER_DIR, "draw_lights.vert")
DRAW_LIGHTS_FRAG = os.path.join(_SHADER_DIR, "draw_lights.frag")
DRAW_LIGHTS_FULLSCREEN_VERT = os.path.join(_SHADER_DIR, "draw_lights_fullscreen.vert")


def pack_r11g11b10(value):
    value = array(value, dtype=float16).view(uint16).astype(int)
    value[0] <<= 17
    value[1] <<= 6
    value[2] >>= 5
    value &= (0xffe00000, 0x001ffc00, 0x000003ff)
    return value[0] | value[1] | value[2]


class PointLightData(object):

    def __init__(
            self,
            position=(0.5, 0.5),
            decay_rate=1.0,
            colour=(1.0, 1.0, 1.0)
        ):
        self.position = position
        self.decay_rate = decay_rate
        self.colour = colour

    def pack(self):
        return array((
            float32(self.position[0]).view(uint32),
            float32(self.position[1]).view(uint32),
            float32(self.decay_rate).view(uint32),
            uint32(pack_r11g11b10(self.colour))
        ), dtype=uint32)

    @staticmethod
    def pack_stream(entries):
        return stack([entry.pack() for entry in entries]).flatten()

    
    def construct_visibility_mesh_x0(self, lines, light_id):
        # https://www.redblobgames.com/articles/visibility/

        # Vertex data layout:
        #   half2   position;
        #   uint16  light_id;
        light_id = uint16(light_id)
        index_buffer = []
        vertex_buffer = [
            (
                uint16(0),
                uint16(0),
                light_id
            )
        ]

        # Add walls keep things contained inside of reasonable bounds
        extra_lines = (
            (0, 0, 0, 1),
            (0, 1, 1, 1),
            (1, 1, 1, 0),
            (1, 0, 0, 0),
        )

        lines = concatenate((lines, extra_lines))

        # A lot of logic just becomes simpler if we up front
        # make everything relative to the light
        lines = lines - (
            self.position[0],
            self.position[1],
            self.position[0],
            self.position[1]
        )

        x0y0_angle = arctan2(lines[:,1], lines[:,0])
        x1y1_angle = arctan2(lines[:,3], lines[:,2])

        # During the transition from -pi -> pi, a disoncontiuity occurs, in order
        # to handle this correctly, we duplicate the line, with the first having both
        # its angles in the [-2pi, 0] range and the second in the [0, 2pi] range.
        angle_diff = x1y1_angle - x0y0_angle
        needs_duplication = abs(angle_diff) >= pi
        if needs_duplication.any():
            offset_x0y0 = needs_duplication & (angle_diff < 0)
            offset_x1y1 = needs_duplication & (angle_diff >= 0)
            x0y0_angle[offset_x0y0] -= 2 * pi
            x1y1_angle[offset_x1y1] -= 2 * pi
            duplicate_lines = lines[needs_duplication]
            x0y0_dup = x0y0_angle[needs_duplication] + 2 * pi
            x1y1_dup = x1y1_angle[needs_duplication] + 2 * pi
            lines = concatenate((lines, duplicate_lines))
            x0y0_angle = concatenate((x0y0_angle, x0y0_dup))
            x1y1_angle = concatenate((x1y1_angle, x1y1_dup))

        line_ids = array(tuple(range(len(lines))))
        sorted_endpoints = concatenate(
            (line_ids, line_ids)
        )[argsort(concatenate((x0y0_angle, x1y1_angle)))]

        open_lines = set()
        vertex_to_id = {}

        for line_id in sorted_endpoints:
            if line_id not in open_lines:
                open_lines.add(line_id)
            else:
                open_lines.remove(line_id)
            print((open_lines))



        return index_buffer, vertex_buffer


    def construct_visibility_mesh__x(self, lines, light_id):

        # Cutting algo, start with a base triangle and proceed
        # to cut out segments based upon the lines extended.

        # A lot of logic just becomes simpler if we up front
        # make everything relative to the light
        lines = lines - (
            self.position[0],
            self.position[1],
            self.position[0],
            self.position[1]
        )

        # Sort the lines by which ever lines cover the most surface
        # when projected onto a circle, since it's more likely they'll
        # prevent us from needing to consider other lines later.
        projected_a = arctan2(lines[:,1], lines[:,0])
        projected_b = arctan2(lines[:,3], lines[:,2])
        angle_diff = projected_b - projected_a
        fixup_diff = abs(angle_diff) >= pi
        if fixup_diff.any():
            angle_diff[fixup_diff] += 2 * pi
        lines = lines[argsort(angle_diff)]

        # Initial vertices are a single trangle around the origin
        triangle_scale = 4 # TODO: base this off the lines
        vertices = [(-4 * triangle_scale, -1 * triangle_scale),
                    (1 * triangle_scale, 4 * triangle_scale),
                    (1 * triangle_scale, 1 * triangle_scale)]

        for line in lines:
            A = line[0:2]
            B = line[2:4]
            # TODO bbox test

            # Planes which form a hull
            Ld = A - B
            Ln = array((Ld[1], -Ld[0]))
            Ln *= 1.0 / norm(Ln)
            Lw = dot(Ln, A)

            # Ensure clockwise A->B
            needs_flip = Lw < 0
            if Lw < 0:
                A, B = B, A
                Ln = -Ln
                Lw = -Lw

            An = array((A[1], -A[0]))
            Bn = array((-B[1], B[0]))
            An *= 1.0 / norm(An)
            Bn *= 1.0 / norm(Bn)
            Aw = dot(An, A)
            Bw = dot(Bn, B)

            # Start simple cutting
            # 1. If our hull intersects nothing, stop.
            #
            # 2. If our hull intersects and is fully contained
            #    within a line segment, we add 4 points and stop:
            #       IntersectionA, A, B, IntersectionB.
            #
            # 3. If our hull intersects, but isn't fully contained,
            #    we will need to start clipping vertices.
            needs_more_advanced_routine = False

            vt0 = vertices[-1]
            a_side_vt0 = dot(An, vt0) - Aw
            b_side_vt0 = dot(Bn, vt0) - Bw
            l_side_vt0 = dot(Ln, vt0) - Lw
            
            for second_vertex_id in range(len(vertices)):
                vt1 = vertices[second_vertex_id]
                a_side_vt1 = dot(An, vt1) - Aw
                b_side_vt1 = dot(Bn, vt1) - Bw
                l_side_vt1 = dot(Ln, vt1) - Lw



                #########################
                # ...broken...
                #########################

                # (2) Insert 4 points if:
                #       vt0 is left of A
                #       vt1 is right of B
                #       vt0 and vt1 are behind Ln
                if (    a_side_vt0 > 0
                        and b_side_vt1 > 0
                        and l_side_vt0 > 0
                        and l_side_vt1 > 0
                ):
                    # https://www.geogebra.org/calculator/dehd8yve
                    ray = array((vt1[0] - vt0[0], vt1[1] - vt0[1]))
                    Aw0 = dot(An, A - vt0[0])
                    Bw0 = dot(Bn, B - vt0[0])
                    intersect_a = vt0[0] + ray * Aw0 / dot(ray, An)
                    intersect_b = vt0[0] + ray * Bw0 / dot(ray, Bn)
                    vertices[second_vertex_id:second_vertex_id] = (
                        intersect_a,
                        A,
                        B,
                        intersect_b,
                    )
                    break

                vt0 = vt1
                a_side_vt0 = a_side_vt1
                b_side_vt0 = b_side_vt1
                l_side_vt0 = l_side_vt1

            if not needs_more_advanced_routine:
                continue

        print("{{{0}}}".format(
            ",".join(
                "({0:f},{1:f})".format(k[0], k[1])
                for k in vertices
            )
        ))

    def construct_visibility_mesh(self, lines, light_id):

        # Cutting algo, start with a base triangle and proceed
        # to cut out segments based upon the lines extended.

        # A lot of logic just becomes simpler if we up front
        # make everything relative to the light
        lines = lines - (
            self.position[0],
            self.position[1],
            self.position[0],
            self.position[1]
        )

        # Sort the lines by which ever lines cover the most surface
        # when projected onto a circle, since it's more likely they'll
        # prevent us from needing to consider other lines later.
        projected_a = arctan2(lines[:,1], lines[:,0])
        projected_b = arctan2(lines[:,3], lines[:,2])
        angle_diff = projected_b - projected_a
        fixup_diff = abs(angle_diff) >= pi
        if fixup_diff.any():
            angle_diff[fixup_diff] += 2 * pi
        lines = lines[argsort(angle_diff)]

        triangle_scale = 2
        vertices = [array((-3 * triangle_scale, 0 * triangle_scale)),
                    array((1 * triangle_scale, 2 * triangle_scale)),
                    array((1 * triangle_scale, -2 * triangle_scale))]


        for x0, y0, x1, y1 in lines:
            
            # Ensure clockwise orientation
            if (x1 * y0 - x0 * y1) < 0:
                x0, y0, x1, y1 = x1, y1, x0, y0

            a = array((x0, y0))
            b = array((x1, y1))
            dba = b - a

            left_n = array((y0, -x0))
            right_n = array((-y1, x1))

            line_n = array((y1 - y0), (x0 - x1))
            line_w = dot(line_n, (x0, x1))

            in_intersection = False
            in_intersection_left = False
            in_intersection_pt = (0, 0)
            intersection_start = 0

            i = 0
            off = 0

            # Iterate until we're sure that we aren't mid
            # intersection.
            while off < len(vertices):
                # This should be the correct thing, but it seems to look better
                # reversed, which could mean either I was initially wrong in my assumptions
                # or theres something off when it comes to doing connections...
                # if dot(right_n, vertices[off]) >= 0:
                if dot(right_n, vertices[off]) <= 0:
                    break
                off += 1

            while i < len(vertices):
                j = i + off
                if j >= len(vertices):
                    j -= len(vertices)
                k = j + 1
                if k >= len(vertices):
                    k = 0

                curr_pt = vertices[j]
                next_pt = vertices[k]

                dpt = next_pt - curr_pt

                left_intersection = ray_line_intersection(a, curr_pt, dpt)
                middle_intersection = line_line_intersection(b, dba, next_pt, dpt)
                right_intersection = ray_line_intersection(b, curr_pt, dpt)
                
                left_ipt = curr_pt + dpt * left_intersection
                middle_ipt = next_pt - dpt * middle_intersection
                right_ipt = curr_pt + dpt * right_intersection

                intersects_left = left_intersection < 1 and left_intersection > 0
                intersects_middle = middle_intersection < 1 and middle_intersection > 0
                intersects_right = right_intersection < 1 and right_intersection > 0

                # Reset intersection progress if something weird is going on
                if in_intersection:
                    if intersects_left and in_intersection_left:
                        in_intersection = False
                    # elif intersects_middle and not in_intersection_left:
                    #     in_intersection = False

                if not in_intersection:
                    # Check if edge is inside of our lines hull.
                    # If it is:
                    #   Insert intersection point, i+=1 (skip the inseted point)
                    #   if hull is fully contained, addition add A, B, intersection#2 (i+=3)
                    # print((intersects_left, intersects_middle, intersects_right))

                    # Fully contained, insert [ia, a, b, ib]
                    if intersects_left and intersects_right:
                        vertices[k:k] = (
                            left_ipt,
                            a,
                            b,
                            right_ipt,
                        )
                        i += 4
                        # Shouldn't be possible for another intersection??

                    # Fully contained, insert [ia, a, im]
                    elif left_intersection and intersects_middle:
                        vertices[k:k] = (
                            left_ipt,
                            a,
                            middle_ipt,
                        )
                        i += 3

                    # Fully contained, insert [im, b, ib]
                    elif intersects_middle and intersects_right:
                        vertices[k:k] = (
                            middle_ipt,
                            b,
                            right_ipt,
                        )
                        i += 3

                    elif intersects_left:
                        in_intersection = True
                        in_intersection_left = True
                        in_intersection_pt = left_ipt
                        intersection_start = k

                    elif intersects_middle:
                        in_intersection = True
                        in_intersection_left = False
                        in_intersection_pt = middle_ipt
                        intersection_start = k

                else:
                    # If curr_pt is totally inside of our hull, pop it (i-=1)
                    # If Intersects:
                    #   add intersection point (also A and B sometimes?) (i+=1 + ?)

                    if intersects_middle or intersects_right:
                        
                        in_intersection = False

                        # Cull all points from intersection_start -> here
                        num_to_removed = k - intersection_start
                        if num_to_removed <= 0:
                            num_to_removed += len(vertices)
                            vertices[intersection_start:] = []
                            vertices[:k] = []
                            intersection_start = 0
                        else:
                            vertices[intersection_start:k] = []
                        i -= num_to_removed

                        if intersects_right and in_intersection_left:
                            vertices[intersection_start:intersection_start] = (
                                in_intersection_pt,
                                a,
                                b,
                                right_ipt,
                            )
                            i += 4
                        elif intersects_right and not in_intersection_left:
                            vertices[intersection_start:intersection_start] = (
                                in_intersection_pt,
                                b,
                                right_ipt,
                            )
                            i += 3
                        elif intersects_middle and in_intersection_left:
                            vertices[intersection_start:intersection_start] = (
                                in_intersection_pt,
                                a,
                                middle_ipt
                            )
                            i += 3
                        elif intersects_middle and not in_intersection_left:
                            vertices[intersection_start:intersection_start] = (
                                in_intersection_pt,
                                middle_ipt
                            )
                            i += 2

                i += 1

        print(lines)
        print("{{{0}}}".format(
            ",".join(
                "({0[0]},{0[1]})".format(vt)
                for vt in vertices
            )
        ))




def ray_line_intersection(rd, a, dpt):
    # https://www.geogebra.org/calculator/dug27m5r
    denom = dpt[0] * rd[1] - dpt[1] * rd[0] # cross(B - A, rd)
    if denom > 0:
        # cross(rd, a) / denom
        return (rd[0] * a[1] - rd[1] * a[0]) / denom
    return -1


def line_line_intersection(a, ab, c, cd):
    # https://www.geogebra.org/calculator/ytnhzgzb
    ac = a - c
    d = ab[0] * cd[1] - cd[1] * ab[0] # cross(AB, CD)
    sign_d = sign(d)
    u = (ac[0] * ab[1] - ac[1] * ab[0]) * sign_d # cross(AC, AB) * sign(d)
    t = (ac[0] * cd[1] - ac[1] * cd[0]) * sign_d # cross(AC, CD) * sign(d)
    if (min(u, t) > 0) and (max(u, t) > abs(d)):
        return u / abs(d)
    return -1