
import os
from math import cos, sin, pi, log2

import numpy

from OpenGL.GL import *

import viewport
import line_bvh

_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DRAW_FULL_SCREEN_PATH = os.path.join(
    _SHADER_DIR, "draw_full_screen.vert"
)

_DRAW_DF_GENERATION_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.DF_GENERATION_FRAG
)

_DOWNRES_DF_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.DF_DOWNRES_FRAG
)

_DRAW_DF_TRACE_TEST_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.DF_TRACING_TEST_FRAG
)

_DRAW_V1_LINE_BVH_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = line_bvh.V1_DRAW_BVH_VERT,
    GL_FRAGMENT_SHADER = line_bvh.V1_DRAW_BVH_FRAG
)

_DRAW_V1_TRACE_TEST_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_TRACING_TEST_FRAG
)

_DRAW_UNIFORM_PROBE_NEIGHBOUR_VISIBILITY = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_NEIGHBOUR_VISIBILITY_FRAG
)

_DRAW_UNIFORM_PROBE_VISIBILITY_DISTANCES = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_VISIBILITY_DISTANCES_FRAG
)

_DRAW_UNIFORM_PROBE_TRACE_RADIANCE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_RADIANCE_SAMPLE_FRAG
)

_DRAW_UNIFORM_PROBE_SPATIAL_FILTER = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_SPATIAL_FILTER_FRAG
)

_DRAW_UNIFORM_PROBE_INTEGRATE_CH = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_CH_INTEGRATE_FRAG
)


_DRAW_UNIFORM_PROBE_INDIRECT_DIFFUSE_SAMPLE_RADIANCE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_INDIRECT_DIFFUSE_SAMPLE_RADIANCE_FRAG
)

_DRAW_UNIFORM_PROBE_SPHERE_TEST = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_SPHERE_TEST_VERT,
    GL_FRAGMENT_SHADER = line_bvh.V1_UP_UNIFORM_PROBE_SPHERE_TEST_FRAG
)

DF_RESOLUTION = 1024
DF_NUM_MIPS = max(1, int(log2(DF_RESOLUTION)) - int(log2(16)))

# USING ONE MIP RUNS FASTER!!!!
DF_NUM_MIPS = 1


PROBE_RESOLUTION = 64
PROBE_SAMPLE_SIZE = 4
PROBE_SAMPLE_RESOLUTION = PROBE_RESOLUTION * PROBE_SAMPLE_SIZE

class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self._test_pos_x = 0.5
        self._test_pos_y = 0.5

        self.draw_lines = True


    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)

        # Can probably be a unorm16
        # df_texture_type = GL_R32F
        df_texture_type = GL_R16

        df_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, df_texture_ptr)
        self._df_texture = df_texture_ptr.value
        glTextureStorage2D(self._df_texture, DF_NUM_MIPS, df_texture_type, DF_RESOLUTION, DF_RESOLUTION)
        glTextureParameteri(self._df_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._df_texture, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._df_texture, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTextureParameteri(self._df_texture, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        self._df_per_mip_framebuffers = [
            viewport.WrappedFramebuffer().add_col_attachment(self._df_texture, mip)
            for mip in range(DF_NUM_MIPS)
        ]

        lines_data = (numpy.array([
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
        ], dtype=numpy.float32)
            * 0.5 + 0.5
        )
    
        lines_data = lines_data.reshape((len(lines_data)//4, 4))
        self._num_lines = len(lines_data)
        lines_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_1D, 1, lines_texture_ptr)
        self._lines_texture = lines_texture_ptr.value
        glTextureStorage1D(self._lines_texture, 1, GL_RGBA32F, self._num_lines)
        glTextureParameteri(self._lines_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._lines_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._lines_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureSubImage1D(
            self._lines_texture, 0, 0,
            self._num_lines,
            GL_RGBA, GL_FLOAT,
            lines_data.tobytes()
        )

        line_bvh_data = line_bvh.build_line_bvh_v1(lines_data)
        self._line_bvh_num_float4 = len(line_bvh_data)
        self._line_bvh_num_nodes = len(line_bvh_data) // 3
        line_bvh_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_1D, 1, line_bvh_texture_ptr)
        self._line_bvh_texture = line_bvh_texture_ptr.value
        glTextureStorage1D(self._line_bvh_texture, 1, GL_RGBA32F, self._line_bvh_num_float4)
        glTextureParameteri(self._line_bvh_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._line_bvh_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._line_bvh_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureSubImage1D(
            self._line_bvh_texture, 0, 0,
            self._line_bvh_num_float4,
            GL_RGBA, GL_FLOAT,
            line_bvh_data.tobytes()
        )

        uniform_probe_neighbour_visibility_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, uniform_probe_neighbour_visibility_ptr)
        self._uniform_probe_neighbour_visibility = uniform_probe_neighbour_visibility_ptr.value
        glTextureStorage2D(self._uniform_probe_neighbour_visibility, 1, GL_R8UI, PROBE_RESOLUTION, PROBE_RESOLUTION)
        glTextureParameteri(self._uniform_probe_neighbour_visibility, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_neighbour_visibility, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_neighbour_visibility, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._uniform_probe_neighbour_visibility, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self._uniform_probe_neighbour_visibility_fb = viewport.WrappedFramebuffer().add_col_attachment(
            self._uniform_probe_neighbour_visibility,
            0
        )

        uniform_probe_vis_distances_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, uniform_probe_vis_distances_ptr)
        self._uniform_probe_vis_distances = uniform_probe_vis_distances_ptr.value
        glTextureStorage2D(
            self._uniform_probe_vis_distances,
            1,
            GL_RGBA32UI,
            PROBE_RESOLUTION,
            PROBE_RESOLUTION
        )
        glTextureParameteri(self._uniform_probe_vis_distances, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_vis_distances, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_vis_distances, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._uniform_probe_vis_distances, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self._uniform_probe_vis_distances_fb = viewport.WrappedFramebuffer().add_col_attachment(
            self._uniform_probe_vis_distances,
            0
        )

        uniform_probe_trace_radiance_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, uniform_probe_trace_radiance_ptr)
        self._uniform_probe_trace_radiance = uniform_probe_trace_radiance_ptr.value
        glTextureStorage2D(
            self._uniform_probe_trace_radiance,
            1,
            GL_R11F_G11F_B10F,
            PROBE_SAMPLE_RESOLUTION,
            PROBE_SAMPLE_RESOLUTION
        )
        glTextureParameteri(self._uniform_probe_trace_radiance, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_trace_radiance, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_trace_radiance, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._uniform_probe_trace_radiance, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self._uniform_probe_trace_radiance_fb = viewport.WrappedFramebuffer().add_col_attachment(
            self._uniform_probe_trace_radiance,
            0
        )

        glCreateTextures(GL_TEXTURE_2D, 1, uniform_probe_trace_radiance_ptr)
        self._uniform_probe_trace_radiance_swap = uniform_probe_trace_radiance_ptr.value
        glTextureStorage2D(
            self._uniform_probe_trace_radiance_swap,
            1,
            GL_R11F_G11F_B10F,
            PROBE_SAMPLE_RESOLUTION,
            PROBE_SAMPLE_RESOLUTION
        )
        glTextureParameteri(self._uniform_probe_trace_radiance_swap, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_trace_radiance_swap, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._uniform_probe_trace_radiance_swap, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._uniform_probe_trace_radiance_swap, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self._uniform_probe_trace_radiance_swap_fb = viewport.WrappedFramebuffer().add_col_attachment(
            self._uniform_probe_trace_radiance_swap,
            0
        )

        probe_texture_settings = {
            GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
            GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
            GL_TEXTURE_MIN_FILTER: GL_LINEAR,
            GL_TEXTURE_MAG_FILTER: GL_LINEAR,
        }
        self._uniform_probe_radiance_ch_0 = viewport.FramebufferTarget(GL_R11F_G11F_B10F, True, probe_texture_settings)
        self._uniform_probe_radiance_ch_1 = viewport.FramebufferTarget(GL_RGBA16F, True, probe_texture_settings)
        self._uniform_probe_radiance_ch_2 = viewport.FramebufferTarget(GL_RG16F, True, probe_texture_settings)
        self._uniform_probe_radiance_ch_fb = viewport.Framebuffer(
            (
                self._uniform_probe_radiance_ch_0,
                self._uniform_probe_radiance_ch_1,
                self._uniform_probe_radiance_ch_2
            ),
            PROBE_RESOLUTION,
            PROBE_RESOLUTION,
        )


        self._uniform_probe_indirect_diffuse_ch_0 = viewport.FramebufferTarget(GL_R11F_G11F_B10F, True, probe_texture_settings)
        self._uniform_probe_indirect_diffuse_ch_1 = viewport.FramebufferTarget(GL_RGB16F, True, probe_texture_settings)
        self._uniform_probe_indirect_diffuse_ch_2 = viewport.FramebufferTarget(GL_RG16F, True, probe_texture_settings)
        self._uniform_probe_indirect_diffuse_ch_fb = viewport.Framebuffer(
            (
                self._uniform_probe_indirect_diffuse_ch_0,
                self._uniform_probe_indirect_diffuse_ch_1,
                self._uniform_probe_indirect_diffuse_ch_2
            ),
            PROBE_RESOLUTION,
            PROBE_RESOLUTION,
        )

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self._generate_line_df()
        self._generate_probe_neighbour_visibility()
        self._generate_probe_sample_radiance()

        glViewport(0, 0, wnd.width, wnd.height)

    def _generate_line_df(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, DF_RESOLUTION, DF_RESOLUTION)
        with self._df_per_mip_framebuffers[0].bind():
            glUseProgram(_DRAW_DF_GENERATION_PROGRAM.get(VS_OUTPUT_UV=0))
            glBindTextureUnit(0, self._lines_texture)
            glUniform1i(0, self._num_lines)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

        # Downscale mips (in practice, this seems to result in more or less the same
        # access pattern as manually retracing it)
        if False:
            glUseProgram(_DOWNRES_DF_PROGRAM.one())
            for mip in range(1, len(self._df_per_mip_framebuffers)):
                glTextureParameteri(self._df_texture, GL_TEXTURE_BASE_LEVEL, mip - 1)
                glTextureParameteri(self._df_texture, GL_TEXTURE_MAX_LEVEL, mip - 1)
                with self._df_per_mip_framebuffers[mip].bind():
                    glBindTextureUnit(0, self._df_texture)
                    glDrawArrays(GL_TRIANGLES, 0, 3)
        # Or retrace against lines
        else:
            for mip in range(1, len(self._df_per_mip_framebuffers)):
                glViewport(0, 0, max(1, DF_RESOLUTION >> mip), max(1, DF_RESOLUTION >> mip))
                with self._df_per_mip_framebuffers[mip].bind():
                    glDrawArrays(GL_TRIANGLES, 0, 3)

        glTextureParameteri(self._df_texture, GL_TEXTURE_BASE_LEVEL, 0)
        glTextureParameteri(self._df_texture, GL_TEXTURE_MAX_LEVEL, len(self._df_per_mip_framebuffers))


    def _generate_probe_neighbour_visibility(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, PROBE_RESOLUTION, PROBE_RESOLUTION)
        with self._uniform_probe_neighbour_visibility_fb.bind():
            glUseProgram(_DRAW_UNIFORM_PROBE_NEIGHBOUR_VISIBILITY.get(
                VS_OUTPUT_UV=0,
                DF_TEXTURE_LOC=0,
                DF_PARAMS_LOC=0
            ))
            glBindTextureUnit(0, self._df_texture)
            bias = 0.5 / (DF_RESOLUTION >> DF_NUM_MIPS)
            glUniform2f(0, bias, DF_NUM_MIPS)
            glUniform2f(1, 1.0/PROBE_RESOLUTION, 1.0/PROBE_RESOLUTION)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

    def _generate_probe_visibility_distances(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, PROBE_RESOLUTION, PROBE_RESOLUTION)
        with self._uniform_probe_vis_distances_fb.bind():
            glUseProgram(_DRAW_UNIFORM_PROBE_VISIBILITY_DISTANCES.get(
                VS_OUTPUT_UV=0,
                DF_TEXTURE_LOC=0,
                DF_PARAMS_LOC=0
            ))
            glBindTextureUnit(0, self._df_texture)
            bias = 0.5 / (DF_RESOLUTION >> DF_NUM_MIPS)
            glUniform2f(0, bias, DF_NUM_MIPS)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

    def _generate_probe_sample_radiance(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, PROBE_SAMPLE_RESOLUTION, PROBE_SAMPLE_RESOLUTION)
        with self._uniform_probe_trace_radiance_fb.bind():
            glUseProgram(_DRAW_UNIFORM_PROBE_TRACE_RADIANCE.get(
                VS_OUTPUT_UV=0,
                DF_TEXTURE_LOC=0,
                DF_PARAMS_LOC=0,
                PROBE_WIDTH=PROBE_SAMPLE_SIZE,
                PROBE_HEIGHT=PROBE_SAMPLE_SIZE
            ))
            glBindTextureUnit(0, self._df_texture)
            bias = 0.5 / (DF_RESOLUTION >> DF_NUM_MIPS)
            glUniform2f(0, bias, DF_NUM_MIPS)
            glUniform4f(
                1,
                PROBE_SAMPLE_RESOLUTION,
                PROBE_SAMPLE_RESOLUTION,
                1.0/PROBE_SAMPLE_RESOLUTION,
                1.0/PROBE_SAMPLE_RESOLUTION
            )
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)


        # Spatial filtering (adds a bit of a nice fade etc)
        # stupid hack: to stop streaks from being visible near
        #              edges, we introduce a tiny bit of bleeding
        #              before filtering with visibility
        glUseProgram(_DRAW_UNIFORM_PROBE_SPATIAL_FILTER.get(
            PROBE_WIDTH=PROBE_SAMPLE_SIZE,
            PROBE_HEIGHT=PROBE_SAMPLE_SIZE,
            NO_BLOCKING=0
        ))
        glBindTextureUnit(0, self._uniform_probe_neighbour_visibility)
        for i in range(2):
            with self._uniform_probe_trace_radiance_swap_fb.bind():
                glBindTextureUnit(1, self._uniform_probe_trace_radiance)
                glDrawArrays(GL_TRIANGLES, 0, 3)
            with self._uniform_probe_trace_radiance_fb.bind():
                glBindTextureUnit(1, self._uniform_probe_trace_radiance_swap)
                glDrawArrays(GL_TRIANGLES, 0, 3)
            glUseProgram(_DRAW_UNIFORM_PROBE_SPATIAL_FILTER.get(
                PROBE_WIDTH=PROBE_SAMPLE_SIZE,
                PROBE_HEIGHT=PROBE_SAMPLE_SIZE,
                NO_BLOCKING=1
            ))

    def _radiance_probe_ch_integrate(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, PROBE_RESOLUTION, PROBE_RESOLUTION)
        with self._uniform_probe_radiance_ch_fb.bind():
            glUseProgram(_DRAW_UNIFORM_PROBE_INTEGRATE_CH.get(
                ACCUMULATE_RADIANCE=True,
                PROBE_WIDTH=PROBE_SAMPLE_SIZE,
                PROBE_HEIGHT=PROBE_SAMPLE_SIZE
            ))
            glBindTextureUnit(0, self._uniform_probe_trace_radiance)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

    def _diffuse_indirect_sample_radiance_probes(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glViewport(0, 0, PROBE_RESOLUTION, PROBE_RESOLUTION)
        with self._uniform_probe_indirect_diffuse_ch_fb.bind():
            glUseProgram(_DRAW_UNIFORM_PROBE_INDIRECT_DIFFUSE_SAMPLE_RADIANCE.get(
                VS_OUTPUT_UV=0,
                PROBE_WIDTH=PROBE_SAMPLE_SIZE,
                PROBE_HEIGHT=PROBE_SAMPLE_SIZE
            ))
            glBindTextureUnit(0, self._uniform_probe_vis_distances)
            glBindTextureUnit(1, self._uniform_probe_radiance_ch_0.texture)
            glBindTextureUnit(2, self._uniform_probe_radiance_ch_1.texture)
            glBindTextureUnit(3, self._uniform_probe_radiance_ch_2.texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)


    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # self._generate_line_df()
        self._generate_probe_neighbour_visibility()
        self._generate_probe_visibility_distances()
        self._generate_probe_sample_radiance()
        self._radiance_probe_ch_integrate()
        self._diffuse_indirect_sample_radiance_probes()

        glViewport(0, 0, wnd.width, wnd.height)
        glBlitNamedFramebuffer(
            self._df_per_mip_framebuffers[0].value,
            0,  # GL_BACK
            0, 0, DF_RESOLUTION, DF_RESOLUTION,
            0, 0, wnd.width, wnd.width,
            GL_COLOR_BUFFER_BIT,
            GL_LINEAR
        )

        if False:
            glUseProgram(_DRAW_V1_TRACE_TEST_PROGRAM.get(
                VS_OUTPUT_UV=0,
                LINE_BVH_V1_LOC=0,
            ))
            glBindTextureUnit(0, self._line_bvh_texture)
            glUniform2f(0, self._test_pos_x, self._test_pos_y)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)
        elif False:
            glUseProgram(_DRAW_DF_TRACE_TEST_PROGRAM.get(
                VS_OUTPUT_UV=0,
                DF_TEXTURE_LOC=0,
                DF_PARAMS_LOC=0
            ))
            glBindTextureUnit(0, self._df_texture)
            bias = 0.5 / (DF_RESOLUTION >> DF_NUM_MIPS)
            glUniform2f(0, bias, DF_NUM_MIPS)
            glUniform2f(1, self._test_pos_x, self._test_pos_y)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)
        else:
            glUseProgram(_DRAW_UNIFORM_PROBE_SPHERE_TEST.get(
                DF_TEXTURE_LOC=0,
                DF_PARAMS_LOC=0
            ))
            glBindTextureUnit(0, self._df_texture)
            bias = 0.5 / (DF_RESOLUTION >> DF_NUM_MIPS)
            glUniform2f(0, bias, DF_NUM_MIPS)
            glUniform4f(
                1,
                PROBE_RESOLUTION,
                PROBE_RESOLUTION,
                1.0/PROBE_RESOLUTION,
                1.0/PROBE_RESOLUTION
            )
            glUniform3f(2, self._test_pos_x, self._test_pos_y, 0.1)
            glBindTextureUnit(1, self._uniform_probe_radiance_ch_0.texture)
            glBindTextureUnit(2, self._uniform_probe_radiance_ch_1.texture)
            glBindTextureUnit(3, self._uniform_probe_radiance_ch_2.texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 6)


        glUseProgram(_DRAW_V1_LINE_BVH_PROGRAM.get(ONLY_LINES=1))
        glBindTextureUnit(0, self._line_bvh_texture)
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_LINES, 0, self._line_bvh_num_nodes * 16)


        wnd.redraw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height
        self._test_pos_x += deriv_u
        self._test_pos_y += -deriv_v
        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
