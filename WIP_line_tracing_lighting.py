
import os
from math import cos, sin, pi, log2
import random

import numpy

from OpenGL.GL import *

import viewport
import line_bvh
import line_bvh.plv1
import perf_overlay_lib

_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DRAW_FULL_SCREEN_PATH = os.path.join(
    _SHADER_DIR, "draw_full_screen.vert"
)

_GEN_PLANE_MAPS_FULL_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.plv1.GEN_PLANE_MAP_FRAG
)

_GEN_BBOX_FROM_PLANE_MAP_FULL_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = line_bvh.plv1.GEN_BBOX_FROM_PLANE_MAP_FRAG
)


_DRAW_POINTLIGHT_BBOXES_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = line_bvh.plv1.DRAW_BBOX_VERT,
    GL_FRAGMENT_SHADER = line_bvh.plv1.DRAW_BBOX_FRAG
)

_DRAW_V1_LINE_BVH_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = line_bvh.V1_DRAW_BVH_VERT,
    GL_FRAGMENT_SHADER = line_bvh.V1_DRAW_BVH_FRAG
)

_DRAW_LIGHTS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = line_bvh.plv1.DRAW_LIGHTS_VERT,
    GL_FRAGMENT_SHADER = line_bvh.plv1.DRAW_LIGHTS_FRAG
)

_DRAW_LIGHTS_FULLSCREEN_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = line_bvh.plv1.DRAW_LIGHTS_FULLSCREEN_VERT,
    GL_FRAGMENT_SHADER = line_bvh.plv1.DRAW_LIGHTS_FRAG
)

LINE_PLANEMAP_RESOLUTION = 64

class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self._fullscreen_draw_lights = 0
        self._draw_pl_bbox = 0
        self._test_pos_x = 0.5
        self._test_pos_y = 0.5

        self.timer_overlay = perf_overlay_lib.TimerSamples256Overlay()


    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)

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

        lights = [
            line_bvh.plv1.PointLightData(
                (0.125, 0.5),
                10.0,
                (1.0, 0.0, 0.0)
            ),
            line_bvh.plv1.PointLightData(
                (0.4, 0.75),
                10.0,
                (0.0, 1.0, 0.0)
            ),
            line_bvh.plv1.PointLightData(
                (0.65, 0.5),
                10.0,
                (0.0, 0.0, 1.0)
            ),
        ]


        # 100 random lights
        # lights = [
        #     line_bvh.plv1.PointLightData(
        #         (random.random() * 0.5 + 0.25, random.random() * 0.5 + 0.25),
        #         1.0 + random.random(),
        #         (random.random() * 0.1, random.random() * 0.1, random.random() * 0.1)
        #     )
        #     for _ in range(100)
        # ]

        self._num_lights = len(lights)

        light_data_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_1D, 1, light_data_texture_ptr)
        self._light_data_texture = light_data_texture_ptr.value
        glTextureStorage1D(self._light_data_texture, 1, GL_RGBA32UI, self._num_lights)
        glTextureParameteri(self._light_data_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._light_data_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._light_data_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureSubImage1D(
            self._light_data_texture, 0, 0,
            self._num_lights,
            GL_RGBA_INTEGER,
            GL_UNSIGNED_INT,
            line_bvh.plv1.PointLightData.pack_stream(lights).tobytes()
        )

        light_planemap_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, light_planemap_ptr)
        self._light_planemap = light_planemap_ptr.value
        glTextureStorage2D(
            self._light_planemap,
            1,
            GL_RGB10_A2,
            LINE_PLANEMAP_RESOLUTION,
            self._num_lights
        )
        glTextureParameteri(self._light_planemap, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._light_planemap, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        # glTextureParameteri(self._light_planemap, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        # glTextureParameteri(self._light_planemap, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTextureParameteri(self._light_planemap, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._light_planemap, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self._light_planemap_fb = viewport.WrappedFramebuffer().add_col_attachment(
            self._light_planemap,
            0
        )

        light_bbox_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_1D, 1, light_bbox_texture_ptr)
        self._light_bbox_texture = light_bbox_texture_ptr.value
        glTextureStorage1D(self._light_bbox_texture, 1, GL_RGBA16F, self._num_lights)
        glTextureParameteri(self._light_bbox_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._light_bbox_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._light_bbox_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self._light_bbox_fb = viewport.WrappedFramebuffer().add_col_attachment(
            self._light_bbox_texture,
            0
        )

        glViewport(0, 0, wnd.width, wnd.height)

    def _generate_plane_maps_full(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        
        # Generate actual plane data
        glViewport(0, 0, LINE_PLANEMAP_RESOLUTION, self._num_lights)
        with self._light_planemap_fb.bind():
            glUseProgram(_GEN_PLANE_MAPS_FULL_PROGRAM.get(
                VS_OUTPUT_UV=0,
                LINE_BVH_V1_LOC=0,
                FLICKERING_POINT_LIGHTS=0
            ))
            glBindTextureUnit(0, self._line_bvh_texture)
            glBindTextureUnit(1, self._light_data_texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

        # Generate BBOX
        glViewport(0, 0, self._num_lights, 1)
        with self._light_bbox_fb.bind():
            glUseProgram(_GEN_BBOX_FROM_PLANE_MAP_FULL_PROGRAM.get(
                FLICKERING_POINT_LIGHTS=0
            ))
            glBindTextureUnit(0, self._light_planemap)
            glBindTextureUnit(1, self._light_data_texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

    def _drawlights_fullscreen(self):
        glEnable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_ONE, GL_ONE)
        glUseProgram(_DRAW_LIGHTS_FULLSCREEN_PROGRAM.get(
            FLICKERING_POINT_LIGHTS=0,
            OUTPUT_CIRCULAR_HARMONICS=0,
        ))
        glBindTextureUnit(0, self._light_data_texture)
        glBindTextureUnit(1, self._light_planemap)
        glUniform1f(0, 1.0 / self._num_lights)
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_TRIANGLES, 0, 3  * self._num_lights)
        glBlendFunc(GL_ONE, GL_ZERO)

    def _drawlights(self):
        glEnable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_ONE, GL_ONE)
        glUseProgram(_DRAW_LIGHTS_PROGRAM.get(
            FLICKERING_POINT_LIGHTS=0,
            OUTPUT_CIRCULAR_HARMONICS=0,
        ))
        glBindTextureUnit(0, self._light_data_texture)
        glBindTextureUnit(1, self._light_planemap)
        glBindTextureUnit(2, self._light_bbox_texture)
        glUniform1f(0, 1.0 / self._num_lights)
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_TRIANGLES, 0, 6 * self._num_lights)
        glBlendFunc(GL_ONE, GL_ZERO)

    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._generate_plane_maps_full()

        glViewport(0, 0, wnd.width, wnd.height)

        if self._fullscreen_draw_lights:
            self._drawlights_fullscreen()
        else:
            self._drawlights()

        glUseProgram(_DRAW_V1_LINE_BVH_PROGRAM.get(ONLY_LINES=1))
        glBindTextureUnit(0, self._line_bvh_texture)
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_LINES, 0, self._line_bvh_num_nodes * 16)

        if self._draw_pl_bbox:
            glUseProgram(_DRAW_POINTLIGHT_BBOXES_PROGRAM.get())
            glBindTextureUnit(0, self._light_bbox_texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_LINES, 0, self._num_lights * 8)

        self.timer_overlay.update(wnd.width, wnd.height)
        wnd.redraw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        if key == b'p':
            self._fullscreen_draw_lights ^= 1
        if key == b'b':
            self._draw_pl_bbox ^= 1
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height
        self._test_pos_x += deriv_u
        self._test_pos_y += -deriv_v
        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
