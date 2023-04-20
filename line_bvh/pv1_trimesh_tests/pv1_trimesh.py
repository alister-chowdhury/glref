from numpy import *

import os
import sys

sys.path.append(os.path.abspath(
    os.path.join(__file__, "..", "..", "..")
))

import line_bvh


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def ccw_weight(dab, dcb):
    numerator = cross(dab, dcb)
    denom = dot(dab, dcb)
    return pi - arctan2(-numerator, -denom)


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
    if denom != 0:
        denom = 1.0 / denom
        t = cross(dpt, a) * denom
        if t >= 0:
            return cross(rd, a) * denom
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


lines_data = (array([
    -0.8, 0.8, -0.8, 0.6,
    -0.8, 0.6, -0.8, 0.4,
    -0.8, 0.4, -0.6, 0.2,
    -0.6, 0.6, -0.6, 0.4,
    -0.6, 0.4, -0.4, 0.2,
    -0.6, 0.4, -0.4550845979179728, 0.4041195074892856,
    -0.4, 0.6, -0.4550845979179728, 0.4041195074892856,
    -0.6, 0.8, -0.3523147896531834, 0.7417917346450221,
    -0.3523147896531834, 0.7417917346450221, -0.16512692459945985, 0.8372208423194695,
    -0.16512692459945985, 0.8372208423194695, 0.11014934753836887, 0.8372208423194695,
    -0.6, 0.8, -0.6000000000000001, 1.0,
    -0.8, 0.8, -0.8, 1.0,
    -0.6, 0.2, -0.6899870168089199, 0.07378798092389112,
    -0.6899870168089199, 0.07378798092389112, -0.8, 0.2,
    -0.8, 0.2, -0.887746417933024, 0.35356291088806213,
    -0.887746417933024, 0.35356291088806213, -0.880247239549394, 0.9309996464275795,
    -0.880247239549394, 0.9309996464275795, -0.930241762106928, 0.9459980031948397,
    -0.930241762106928, 0.9459980031948397, -0.9477398450020649, 0.34856345863230875,
    -0.9477398450020649, 0.34856345863230875, -0.9252423098511745, 0.17608235580881654,
    -0.9252423098511745, 0.17608235580881654, -0.7552609331555589, 0.00860070524107772,
    -0.7552609331555589, 0.00860070524107772, -0.83775189537549, -0.12138505340851061,
    -0.83775189537549, -0.12138505340851061, -0.8227535386082299, -0.491344520334262,
    -0.8227535386082299, -0.491344520334262, -0.9269466685747265, -0.5956512742156619,
    -0.9269466685747265, -0.5956512742156619, -0.9201292336805172, -0.6910953627345904,
    -0.9201292336805172, -0.6910953627345904, -0.797415405584752, -0.5592916214465462,
    -0.797415405584752, -0.5592916214465462, -0.6474318379121501, -0.7365449286959849,
    0.5434601240897526, 0.16422840418542378, 0.5456683846785265, 0.3320562089322359,
    -0.6474318379121501, -0.7365449286959849, -0.8, -0.8,
    -0.8, -0.8, -0.9396871437734609, -0.9341363891990299,
    -0.9396871437734609, -0.9341363891990299, -0.8434533432399988, -0.9549436974224811,
    -0.8434533432399988, -0.9549436974224811, -0.7628250238741252, -0.8483062427772933,
    -0.7628250238741252, -0.8483062427772933, -0.6, -0.8,
    -0.6, -0.8, -0.45591722757821923, -0.8769162915845389,
    -0.45591722757821923, -0.8769162915845389, -0.1047939013074794, -0.8743153780566074,
    -0.1047939013074794, -0.8743153780566074, -0.12039938247506783, -0.9367373027269612,
    -0.12039938247506783, -0.9367373027269612, -0.026766495469537206, -0.9653473515342067,
    -0.026766495469537206, -0.9653473515342067, 0.0, -0.8795172051124702,
    0.0, -0.8795172051124702, -0.05797745780471408, -0.7546733557717626,
    -0.05797745780471408, -0.7546733557717626, -0.4273071787709738, -0.7702788369393511,
    -0.4273071787709738, -0.7702788369393511, -0.627577520421692, -0.5804121494003581,
    -0.627577520421692, -0.5804121494003581, -0.37268799468441427, -0.43736190536413067,
    -0.37268799468441427, -0.43736190536413067, -0.2244359235923241, -0.46597195417137616,
    -0.2244359235923241, -0.46597195417137616, -0.3830916487961399, -0.5622057547048382,
    -0.3830916487961399, -0.5622057547048382, -0.3752889082123457, -0.6506368146545062,
    -0.3752889082123457, -0.6506368146545062, -0.3102660700140605, -0.6714441228779575,
    -0.3102660700140605, -0.6714441228779575, -0.30246332943026627, -0.5856139764562209,
    -0.30246332943026627, -0.5856139764562209, -0.011161014301948767, -0.4789765218110332,
    -0.011161014301948767, -0.4789765218110332, 0.0, -0.4,
    0.0, -0.4, -0.3440779458771688, -0.31771988307928584,
    -0.3440779458771688, -0.31771988307928584, -0.6613893962848003, -0.48938017592275884,
    -0.6613893962848003, -0.48938017592275884, -0.6899994450920458, -0.12265136848443012,
    -0.6899994450920458, -0.12265136848443012, -0.5235409793044358, 0.13743998430871082,
    -0.5235409793044358, 0.13743998430871082, -0.3960962164357969, 0.03340344319145445,
    -0.3960962164357969, 0.03340344319145445, -0.5729583363351325, -0.1486605037637442,
    -0.5729583363351325, -0.1486605037637442, -0.5651555957513383, -0.2839080072161775,
    -0.5651555957513383, -0.2839080072161775, -0.48972910344132753, -0.29691257485583455,
    -0.48972910344132753, -0.29691257485583455, -0.4689217952178763, -0.16426598493133265,
    -0.4689217952178763, -0.16426598493133265, -0.3180688105978547, -0.013413000311310921,
    -0.3180688105978547, -0.013413000311310921, -0.09178933366782237, -0.1746696390430583,
    -0.09178933366782237, -0.1746696390430583, -0.17761948008955877, -0.2344906501854807,
    -0.17761948008955877, -0.2344906501854807, -0.021564668413674392, -0.35153175894239413,
    -0.021564668413674392, -0.35153175894239413, 0.08507278623151326, -0.3411281048306685,
    0.08507278623151326, -0.3411281048306685, -0.01636284135781158, -0.2500961313530692,
    -0.01636284135781158, -0.2500961313530692, 0.09547644034323889, -0.1746696390430583,
    0.09547644034323889, -0.1746696390430583, 0.10848100798289592, -0.04462396264648783,
    0.10848100798289592, -0.04462396264648783, -0.20622952889680424, 0.06981623258249418,
    -0.20622952889680424, 0.06981623258249418, 0.04605908331254217, 0.17125186017181915,
    0.04605908331254217, 0.17125186017181915, 0.19171024087670094, 0.11143084902939673,
    0.19171024087670094, 0.11143084902939673, 0.27754038729843733, -0.12265136848443012,
    0.27754038729843733, -0.12265136848443012, 0.19691206793256374, -0.3437290183585999,
    0.19691206793256374, -0.3437290183585999, 0.2203202896839464, -0.6376322470148492,
    0.2203202896839464, -0.6376322470148492, 0.1396919703180728, -0.7286642204924485,
    0.1396919703180728, -0.7286642204924485, 0.13709105679014139, -0.8977235998079901,
    0.39458149605535064, -0.9185309080314413, 0.13709105679014139, -0.8977235998079901,
    0.39458149605535064, -0.9185309080314413, 0.6962874652953938, -0.858709896889019,
    0.6962874652953938, -0.858709896889019, 0.8445395363874839, -0.7104578257969286,
    0.8445395363874839, -0.7104578257969286, 0.8393377093316211, -0.5205911382579358,
    0.8393377093316211, -0.5205911382579358, 0.7222966005747078, -0.4529673865317191,
    0.7222966005747078, -0.4529673865317191, 0.4, -0.6,
    0.4, -0.6, 0.3035495225777514, -0.32812353719101145,
    0.3035495225777514, -0.32812353719101145, 0.4335951989743217, -0.1460595902358128,
    0.4335951989743217, -0.1460595902358128, 0.4335951989743217, 0.04640801083111149,
    0.5434601240897526, 0.16422840418542378, 0.4335951989743217, 0.04640801083111149,
    0.537631740091578, -0.6636413822941633, 0.5350308265636465, -0.7364669610762428,
    0.5350308265636465, -0.7364669610762428, 0.6156591459295202, -0.7494715287158997,
    0.6156591459295202, -0.7494715287158997, 0.6286637135691772, -0.6532377281824376,
    0.6286637135691772, -0.6532377281824376, 0.537631740091578, -0.6636413822941633,
    -0.4, 0.2, -0.26084871298336376, 0.22066921720251592,
    -0.26084871298336376, 0.22066921720251592, -0.26605054003922657, 0.4417468670766857,
    -0.26605054003922657, 0.4417468670766857, -0.4, 0.6,
    -0.27905510767888364, 0.6628245169508555, -0.16201399892197033, 0.5145724458587652,
    -0.16201399892197033, 0.5145724458587652, -0.13860577717058767, 0.28309114187286977,
    -0.13860577717058767, 0.28309114187286977, 0.0, 0.2986966230404582,
    0.0, 0.2986966230404582, 0.06946730506392483, 0.44694869413254856,
    0.06946730506392483, 0.44694869413254856, -0.01636284135781158, 0.5613888893615305,
    -0.01636284135781158, 0.5613888893615305, -0.27905510767888364, 0.6628245169508555,
    -0.1464085177543819, 0.7174437010374151, 0.0, 0.6732281710625811,
    0.0, 0.6732281710625811, 0.13449014326220998, 0.6940354792860324,
    -0.1464085177543819, 0.7174437010374151, -0.047573803692988456, 0.7564574039563863,
    -0.047573803692988456, 0.7564574039563863, 0.37117327430396796, 0.7616592310122491,
    0.37117327430396796, 0.7616592310122491, 0.5922509241781375, 0.8891039938808881,
    0.5922509241781375, 0.8891039938808881, 0.5558381347870978, 0.9463240914953791,
    0.5558381347870978, 0.9463240914953791, 0.4205906313346647, 0.9541268320791734,
    0.4205906313346647, 0.9541268320791734, 0.29574678199395715, 0.8708975991853682,
    0.29574678199395715, 0.8708975991853682, 0.11014934753836887, 0.8372208423194695,
    0.13449014326220998, 0.6940354792860324, 0.6, 0.6,
    0.6, 0.6, 0.7274984276305706, 0.7252464416212093,
    0.7274984276305706, 0.7252464416212093, 0.8809523257785236, 0.7070400469256894,
    0.8809523257785236, 0.7070400469256894, 0.9485760775047402, 0.4365450400208229,
    0.9485760775047402, 0.4365450400208229, 0.8653468446109351, 0.31430210420804666,
    0.8653468446109351, 0.31430210420804666, 0.909562374585769, 0.14784363842043646,
    0.909562374585769, 0.14784363842043646, 0.8757504987226608, -0.23969247724134354,
    0.8757504987226608, -0.23969247724134354, 0.774314871133336, -0.32812353719101145,
    0.774314871133336, -0.32812353719101145, 0.6702783300160797, -0.33072445071894285,
    0.6702783300160797, -0.33072445071894285, 0.6260628000412458, -0.29431166132790315,
    0.6260628000412458, -0.29431166132790315, 0.7066911194071194, -0.23969247724134354,
    0.7066911194071194, -0.23969247724134354, 0.7665121305495417, -0.1486605037637442,
    0.7665121305495417, -0.1486605037637442, 0.7535075629098847, 0.11403176255732814,
    0.7535075629098847, 0.11403176255732814, 0.6676774164881483, 0.2622838336494185,
    0.6676774164881483, 0.2622838336494185, 0.6546728488484913, 0.07241714611042559,
    0.6546728488484913, 0.07241714611042559, 0.704090205879188, -0.07843583850959615,
    0.704090205879188, -0.07843583850959615, 0.6988883788233251, -0.1694678119871955,
    0.563640875370892, -0.20327968785030381, 0.6988883788233251, -0.1694678119871955,
    0.563640875370892, -0.20327968785030381, 0.511622604812264, -0.1200504549564987,
    0.511622604812264, -0.1200504549564987, 0.5194253453960581, -0.026417567950967967,
    0.5194253453960581, -0.026417567950967967, 0.5684412929393573, 0.03552596459056943,
    0.5684412929393573, 0.03552596459056943, 0.6, 0.2,
    0.6, 0.2, 0.5456683846785265, 0.3320562089322359,
    0.7092095515335306, 0.5854019747240594, 0.8, 0.6,
    0.8, 0.6, 0.845578802046636, 0.5282148696701765,
    0.845578802046636, 0.5282148696701765, 0.8015887212359569, 0.4490327242109539,
    0.8015887212359569, 0.4490327242109539, 0.7092095515335306, 0.5854019747240594,
    0.29350328787261243, 0.46882826057575955, 0.2957027919131464, 0.4358356999677501,
    0.2957027919131464, 0.4358356999677501, 0.33529386464275773, 0.433636195927216,
    0.33529386464275773, 0.433636195927216, 0.3385147229981519, 0.4738969253696431,
    0.2957027919131464, 0.4358356999677501, 0.29350328787261243, 0.46882826057575955,
    0.3385147229981519, 0.4738969253696431, 0.29350328787261243, 0.46882826057575955,
    0.3007526633482028, 0.3773906350299966, 0.33785944567776255, 0.3690116841813863,
    0.33785944567776255, 0.3690116841813863, 0.34025343163450833, 0.2181905689064014,
    0.34025343163450833, 0.2181905689064014, 0.3139195861103046, 0.2134025969929098,
    0.3007526633482028, 0.3773906350299966, 0.3139195861103046, 0.2134025969929098,
    0.10683980085179354, 0.2840251827169107, 0.16668944977043837, 0.36542070524626763,
    0.16668944977043837, 0.36542070524626763, 0.20259923912162525, 0.3522537824841658,
    0.20259923912162525, 0.3522537824841658, 0.21217518294860843, 0.24093343549548643,
    0.21217518294860843, 0.24093343549548643, 0.17387140764067574, 0.23016049869013036,
    0.17387140764067574, 0.23016049869013036, 0.10683980085179354, 0.2840251827169107,
    0.443551169724851, 0.5370401714419458, 0.4820518845461652, 0.42328805946988135,
    0.4820518845461652, 0.42328805946988135, 0.5853038015669625, 0.41453789701049176,
    0.5853038015669625, 0.41453789701049176, 0.6343047113395442, 0.4792890992099746,
    0.6343047113395442, 0.4792890992099746, 0.443551169724851, 0.5370401714419458,
    0.1285453211868255, 0.614041601084574, 0.14079554862997093, 0.5492903988850911,
    0.14079554862997093, 0.5492903988850911, 0.22654714073198898, 0.5160397815394108,
    0.22654714073198898, 0.5160397815394108, 0.2562976930939136, 0.5772909187551378,
    0.2562976930939136, 0.5772909187551378, 0.1285453211868255, 0.614041601084574,


    # -1, -1, -1, 1,
    # -1, 1, 1, 1,
    # 1, 1, 1, -1,
    # 1, -1, -1, -1,


    # -10, -10, -10, 10,
    # -10, 10, 10, 10,
    # 10, 10, 10, -10,
    # 10, -10, -10, -10,


], dtype=float32)
    * 0.5 + 0.5
)
lines_data = lines_data.reshape((len(lines_data)//4, 4))


total_iterations = 0




def trace_ray(bvh, origin, ray):
    intersection = line_bvh.trace_line_bvh_v1(bvh, origin, ray, 10.0, False)
    # Handle no intersection by adding virtual lines
    if intersection.hit_line_id == 0xffffffff:
        for i in range(4):
            # [0, 0] => [1, 1] box
            x0 = i & 1
            y0 = (i >> 1) & 1
            x1 = (i + 1) & 1
            y1 = ((i + 1) >> 1) & 1

            a = array((x0, y0)) - origin
            dpt = array((x1, y1)) - array((x0, y0))
            interval = ray_line_intersection_ro0(ray, a, dpt)

            if interval >= 0 and interval <= 1:
                intersection.hit_line_interval = interval
                intersection_point = array((x0, y0)) + interval * dpt
                intersection.hit_line_id = 0xffffffff - i
                intersection.duv = intersection_point - origin
                intersection.hit_dist_sq = intersection.duv[0]**2 + intersection.duv[1]**2
                break
    return intersection



def binary_search_trace(origin, bvh, prev_end, new_start, max_iterations=1024):
    vertices = []
    while max_iterations > 0:
        max_iterations -= 1
        ray = prev_end[1] + new_start[1]
        norm_factor = sqrt(ray[0]**2 + ray[1]**2)
        ray /= norm_factor
        # new_intersection = line_bvh.trace_line_bvh_v1(bvh, origin, ray, 10.0, False)
        new_intersection = trace_ray(bvh, origin, ray)
        global total_iterations
        total_iterations += 1
        if new_intersection.hit_line_id == prev_end[0].hit_line_id:
            prev_end = (new_intersection, ray)
        elif new_intersection.hit_line_id == new_start[0].hit_line_id:
            new_start = (new_intersection, ray)
        else:
            # We've encountered a new line and need to split events
            new_prev_end = (new_intersection, ray)
            vertices.extend(
                binary_search_trace(origin, bvh, prev_end, new_prev_end, max_iterations)
            )
            prev_end = new_prev_end

        # Realistically hit our limit 
        if norm_factor >= 1.99999988079:
            break

    # We should just need to detect if events (not simply lines) intersect, if they do, insert
    # the intersection as a vertex.
    # If they do not intersect, project a ray from the closer hit hit backwards
    # and insert either (A, intersection), (intersection, B) ?
    #
    # For now, we're just going to be hacky and store the intersection positions
    vertices.append(origin + prev_end[0].duv)
    vertices.append(origin + new_start[0].duv)
    return vertices



def construct_visibility_mesh(origin, bvh, lines):

    thetas_0 = arctan2(lines[:,1] - origin[1], lines[:,0] - origin[0])
    thetas_1 = arctan2(lines[:,3] - origin[1], lines[:,3] - origin[0])
    thetas = concatenate((thetas_0, thetas_1))
    # Adding extra rays just to deal with the possibility of missing a vertex
    thetas = concatenate((thetas, thetas + 1e-10, thetas - 1e-10))
    thetas.sort()
    thetas = unique(thetas)

    rays = column_stack((cos(thetas), sin(thetas)))

    intersections = [
        # (line_bvh.trace_line_bvh_v1(bvh, origin, ray, 10.0, False), ray)
        (trace_ray(bvh, origin, ray), ray)
        for ray in rays
    ]


    # Only keep start end events, which mark the transition between line segments.
    # at the moment we're not handling "holes", but really should.
    #
    # As a side note, given the set of lines that intersect, we could create a mini bvh
    # on per light basis, although that doesn't seem massively scalable.
    intersection_events = []

    for i in range(len(intersections)):
        if intersections[i][0].hit_line_id != intersections[i-1][0].hit_line_id:
            intersection_events.append((intersections[i-1], intersections[i]))

    vertices = []
    for prev_end, new_start in intersection_events:
        vertices.extend(
            binary_search_trace(origin, bvh, prev_end, new_start)
        )

    # Remove degenerate vertices
    i = 0
    while i < len(vertices):
        a = vertices[i]
        b = vertices[i - 1]
        dab = b - a
        if dot(dab, dab) < 1e-7:
            vertices[i-1] = (vertices[i-1] + vertices[i]) * 0.5
            vertices.pop(i)
            continue
        i += 1

    # Remove degenerate triangles
    i = 0
    while i < len(vertices):
        a = vertices[i]
        b = vertices[i - 2]
        dab = b - a
        if dot(dab, dab) < 1e-7:
            vertices[i-2] = (vertices[i-2] + vertices[i]) * 0.5
            vertices.pop(i)
            vertices.pop(i-1)
            i -= 1
            if i < 0:
                i = 0
            continue
        i += 1

    # Add a pass to make segments which basically make up the same line
    # continous

    queued_indices = list(range(len(vertices)))
    index_buffer = []


    while len(queued_indices) > 2:

        i = 0
        while i < len(queued_indices):
            ia = queued_indices[i - 1]
            ib = queued_indices[i]
            ic = queued_indices[(i + 1) % len(queued_indices)]
            a = vertices[ia]
            b = vertices[ib]
            c = vertices[ic]

            # Stay on the correct side
            N = array((b[1] - a[1], a[0] - b[0]))
            w = dot(N, b)
            if (dot(N, c) - w) < 0:

                # Make sure a->c doesn't intersect with anything
                ok = True
                ca = c - a
                for j in range(len(vertices)):
                    cmpa = vertices[j - 1]
                    cmpb = vertices[j]
                    interval = line_line_intersection(a, ca, cmpa, cmpb-cmpa)
                    if interval > (1e-10) and interval < (1 - 1e-10):
                        ok = False
                        break

                if ok:
                    index_buffer.append((ia, ib, ic))
                    queued_indices.pop(i)
                    continue

            i += 1
            # print(len(queued_indices))


            # if(len(queued_indices) < 3):
            #     break
            # if len(queued_indices) == 3:
            #     queued_indices = []

        # if len(queued_indices) == 4:
        #     print("{{{0}}}".format(
        #         ",".join(
        #             "({0[0]:f},{0[1]:f})".format(vertices[queued_indices[i]])
        #             for i in range(len(queued_indices))
        #         )
        #     ))
        #     exit()



    lines_debug = []
    for i in range(len(vertices)):
        lines_debug.append((vertices[i-1][0], vertices[i-1][1], vertices[i][0], vertices[i][1]))

    lines_debug = []
    for a, b, c in index_buffer:
        a = vertices[a]
        b = vertices[b]
        c = vertices[c]
        lines_debug.append((a[0], a[1], b[0], b[1]))
        lines_debug.append((b[0], b[1], c[0], c[1]))
        lines_debug.append((c[0], c[1], a[0], a[1]))


    # lines_debug = [
    #     (
    #         event[0].line[0],
    #         event[0].line[1],
    #         event[0].line[0] - event[0].line[2],
    #         event[0].line[1] - event[0].line[3]
    #     )
    #     for event, _ in intersection_events
    # ]
    print("{{{0}}}".format(
        ",".join(
            "segment(({0[0]:f},{0[1]:f}),({0[2]:f},{0[3]:f}))".format(line)
            for line in lines_debug
        )
    ))

    # for a, b in intersection_events:
        # print(a[0].hit_line_id, b[0].hit_line_id)
        # print(a[2], b[2])
    # print(sorted(a[0].hit_line_id for a, b in intersection_events))





if __name__ == "__main__":

    bvh = line_bvh.build_line_bvh_v1(lines_data)
    # origin = array((0.125, 0.5))
    # origin = array((0.4, 0.75))
    # origin = array((0.65, 0.5))
    # origin = array((0.55, 0.25))
    origin = array((0.4,0.57))
    construct_visibility_mesh(origin, bvh, lines_data)
    print(total_iterations)
