import os
from math import cos, sin, pi

import numpy

from OpenGL.GL import *
from OpenGL.arrays.arraydatatype import ArrayDatatype
from OpenGL.GL.EXT import texture_compression_s3tc

import viewport
import perf_overlay_lib


_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DRAW_SHARED_VISION_PATH = os.path.join(
    _SHADER_DIR, "stencil_shared_vision_generate_shadow.vert"
)

_DRAW_SHARED_VISION_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER=_DRAW_SHARED_VISION_PATH
)

_DRAW_LINES_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "shared_vision_draw_lines.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "shared_vision_draw_lines.frag")
)


DRAW_STENCIL_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) uniform float layerId;

void main()
{
    gl_Position = vec4(uv, layerId, 1.0);
}
"""


DRAW_DEBUGOFFSET_STENCIL_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) uniform float layerId;
layout(location = 1) uniform vec2 debugOffset;

void main()
{
    gl_Position = vec4(uv+debugOffset, layerId, 1.0);
}
"""


DRAW_SHAPE_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) out vec2 outUv;

layout(location = 0) uniform float layerId;

void main()
{
    outUv = uv * 0.5 + 0.5;
    gl_Position = vec4(uv, layerId, 1.0);
}
"""


DRAW_SHAPE_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outCol;
layout(location = 1) uniform vec4 col;

void main()
{
    outCol = col;
}
"""

DRAW_TEXTURE_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outCol;

layout(binding = 0) uniform sampler2DArray inputTexture;


void main()
{
    outCol = texture(inputTexture, vec3(uv, 11.));
}
"""

DRAW_FOW_INIT_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) out vec2 outUv;

void main()
{
    outUv = uv * 0.5 + 0.5;
    gl_Position = vec4(uv, 0., 1.0);
}
"""

DRAW_FOW_INIT_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;

layout(binding = 0) uniform sampler2D inputTexture;

void main()
{
    if(texture(inputTexture, uv).x < 0.5) { discard; }
}
"""

DRAW_FOW_HISTORY_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(location = 0) out float outCol;

void main()
{
    outCol = 1.0;
}
"""




def generate_bw_bc1_block(
        a, b, c, d,
        e, f, g, h,
        i, j, k, l,
        m, n, o, p):
    # value = [0, 3] 0 = black, 3 = white
    # https://docs.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression
    # https://www.khronos.org/opengl/wiki/S3_Texture_Compression#:~:text=A%20DXT1%2Dcompressed%20image%20is,internal%20format%20of%20the%20image.
    bits = 0
    for x in (
            d, c, b, a,
            h, g, f, e,
            l, k, j, i,
            p, o, n, m
    ):
        bits <<= 2
        bits |= x

    return numpy.array([
        0xffff0000,    # colour 1, 2
        # bits,
        bits
    ], dtype=numpy.uint32)


def generate_fog_of_war_texture():
    # https://technology.riotgames.com/sites/default/files/fow_diagram.png
    # A B
    # C D
    # Corresponds to the following bit address 0bABCD
    # Output texture is BC1 64x4 | 4x64 \ 4x4x16
    B = 0
    W = 1
    G = 2
    m0000 = generate_bw_bc1_block(
        B, B, B, B,
        B, B, B, B,
        B, B, B, B,
        B, B, B, B,
    )
    m0001 = generate_bw_bc1_block(
        B, B, B, B,
        B, B, B, B,
        B, B, B, G,
        B, B, G, W,
    )
    m0010 = generate_bw_bc1_block(
        B, B, B, B,
        B, B, B, B,
        G, B, B, B,
        W, G, B, B,
    )
    m0011 = generate_bw_bc1_block(
        B, B, B, B,
        B, B, B, B,
        W, W, W, W,
        W, W, W, W,
    )
    m0100 = generate_bw_bc1_block(
        B, B, G, W,
        B, B, B, G,
        B, B, B, B,
        B, B, B, B,
    )
    m0101 = generate_bw_bc1_block(
        B, B, W, W,
        B, B, W, W,
        B, B, W, W,
        B, B, W, W,
    )
    m0110 = generate_bw_bc1_block(
        B, B, G, W,
        B, B, B, G,
        G, B, B, B,
        W, G, B, B,
    )
    m0111 = generate_bw_bc1_block(
        W, W, W, W,
        W, W, W, W,
        W, W, W, G,
        W, W, G, B,
    )
    m1000 = generate_bw_bc1_block(
        W, G, B, B,
        G, B, B, B,
        B, B, B, B,
        B, B, B, B,
    )
    m1001 = generate_bw_bc1_block(
        W, G, B, B,
        G, B, B, B,
        B, B, B, G,
        B, B, G, W,
    )
    m1010 = generate_bw_bc1_block(
        W, W, B, B,
        W, W, B, B,
        W, W, B, B,
        W, W, B, B,
    )
    m1011 = generate_bw_bc1_block(
        W, W, G, B,
        W, W, W, G,
        W, W, W, W,
        W, W, W, W,
    )
    m1100 = generate_bw_bc1_block(
        W, W, W, W,
        W, W, W, W,
        B, B, B, B,
        B, B, B, B,
    )
    m1101 = generate_bw_bc1_block(
        W, W, W, W,
        W, W, W, W,
        G, W, W, W,
        B, G, W, W,
    )
    m1110 = generate_bw_bc1_block(
        W, W, W, W,
        W, W, W, W,
        W, W, W, G,
        W, W, G, B,
    )
    m1111 = generate_bw_bc1_block(
        W, W, W, W,
        W, W, W, W,
        W, W, W, W,
        W, W, W, W,
    )
    return numpy.concatenate((
        m0000,
        m0001,
        m0010,
        m0011,
        m0100,
        m0101,
        m0110,
        m0111,
        m1000,
        m1001,
        m1010,
        m1011,
        m1100,
        m1101,
        m1110,
        m1111,
    )).tobytes()





class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self._draw_lines = False
        self._fow_debug_offset = [0, 0]
        self.timer_overlay = perf_overlay_lib.TimerSamples256Overlay()

    def run(self):
        self.window.run()

    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glDisable(GL_CULL_FACE)

        fow_bytes = generate_fog_of_war_texture()

        self._fow_image_ptr = ctypes.c_int()

        glGenTextures(1, self._fow_image_ptr)
        glBindTexture(GL_TEXTURE_2D_ARRAY, self._fow_image_ptr.value)
        glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glCompressedTexImage3D(
            GL_TEXTURE_2D_ARRAY,
            0,
            texture_compression_s3tc.GL_COMPRESSED_RGBA_S3TC_DXT1_EXT,
            4,
            4,
            16,
            0,
            # len(fow_bytes), # pyopengl omits this
            fow_bytes,
        )
        glBindTexture(GL_TEXTURE_2D_ARRAY, 0)


        self.players =[
            [-0.704384548584,0.8338315304911],
            [-0.2814942390868,0.135869236065],
            [0.3361222420398,-0.7242188225105],
            [0.7372218132636,0.3643838825913],
            [-0.719587913318,-0.5339193806787],
            [-0.5247321451927,0.4964138589975],
            [-0.1270128376493,0.208134092456]
        ]

        lines_data = numpy.array([
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


        # self.players =[
        #     [0, -0.5],
        # ]
        # lines_data = numpy.array([
        #     0.030371951072,0.18523100742,-0.6129894535719,-0.3110763618748
        # ], dtype=numpy.float32)

        self.num_lines = len(lines_data) // 4

        self._line_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_1D, 1, self._line_texture_ptr)
        self._line_texture = self._line_texture_ptr.value

        glTextureParameteri(self._line_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._line_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST )
        glTextureParameteri(self._line_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST )

        glTextureStorage1D(
            self._line_texture,
            1,
            GL_RGBA32F,
            self.num_lines
        )
        glTextureSubImage1D(
            self._line_texture, 0, 0,
            self.num_lines,
            GL_RGBA, GL_FLOAT,
            lines_data
        )



        triangle_indicies = numpy.array([
            0, 1, 2
        ], dtype=numpy.uint32)

        self.triangle_0 = viewport.StaticGeometry(
            (2,),
            triangle_indicies,
            numpy.array([
                0.2, 0.2,
                0.6, 0.2,
                0.4, 0.4
            ], dtype=numpy.float32),
        )

        self.triangle_1 = viewport.StaticGeometry(
            (2,),
            triangle_indicies,
            numpy.array([
                0.2-0.1, 0.8,
                0.4-0.1, 0,
                0.6-0.1, 0.8
            ], dtype=numpy.float32),
        )

        self.triangle_both = viewport.StaticGeometry(
            (2,),
            numpy.array([0, 1, 2,
                # 3, 4, 5
            ]),
            numpy.array([
                0.2-0.2, 0.2,
                0.6-0.2, 0.2,
                0.4-0.2, 0.4,
                # 0.2-0.2, 0.8,
                # 0.4-0.2, 0,
                # 0.6-0.2, 0.8
            ], dtype=numpy.float32),
        )

        self.triangle_screen = viewport.StaticGeometry(
            (2,),
            triangle_indicies,
            numpy.array([
                -4, -1,
                1, -1,
                1, 4
            ], dtype=numpy.float32),
        )

        self._draw_stencil_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_STENCIL_VERTEX_SHADER_SOURCE,
        )

        # Yolo hack for fow history
        self._debugoffset_draw_stencil_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_DEBUGOFFSET_STENCIL_VERTEX_SHADER_SOURCE,
        )

        self._draw_shape_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_SHAPE_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_SHAPE_FRAGMENT_SHADER_SOURCE,
        )

        self._draw_texture_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_SHAPE_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_TEXTURE_FRAGMENT_SHADER_SOURCE,
        )

        # Frame buffer for on screen visibility
        self._shared_vis_fb_col = viewport.FramebufferTarget(GL_RGB32F, True)
        # depth24_s8 on mobile
        self._shared_vis_fb_depth = viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True)
        self._shared_vis_fb = viewport.Framebuffer(
            (self._shared_vis_fb_col, self._shared_vis_fb_depth),
            wnd.width,
            wnd.height
        )


        self._draw_fow_init_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_FOW_INIT_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_FOW_INIT_FRAGMENT_SHADER_SOURCE,
        )

        self._draw_fow_history_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_FOW_INIT_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_FOW_HISTORY_FRAGMENT_SHADER_SOURCE,
        )

        # Frame buffer which records the shared visibility on an entire grid per update
        # depth24_s8 on mobile
        self._fow_fb_depth = viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True)
        self._fow_fb = viewport.Framebuffer((self._fow_fb_depth,), 512, 512)


        # Frame buffer which records the shared visibility history
        self._fow_history_fb_col = viewport.FramebufferTarget(GL_R8, True)
        self._fow_history_fb = viewport.Framebuffer(
            (
                viewport.ProxyFramebufferTarget(self._fow_fb_depth),
                self._fow_history_fb_col
            ),
            512,
            512
        )

        # Clear the initial history, although this should probably be uploaded
        # in the future
        with self._fow_history_fb.bind():
            glClear(GL_COLOR_BUFFER_BIT)

        glClearColor(0.5, 0.5, 0.5, 0.0)

        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):

        # FOW update
        glViewport(0, 0, 512, 512)
        with self._fow_fb.bind():
            # Set the depth to 0 for any previously visible cells, causing
            # the depth test to fail on subsequent occlusion draws
            glStencilMask(0xFF)
            glClear(GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

            glUseProgram(self._draw_fow_init_program)
            glBindTextureUnit(0, self._fow_history_fb_col.value)
            self.triangle_screen.draw()

            # Draw occlusion

            # Dont write to depth
            glDepthMask(GL_FALSE)

            glUseProgram(_DRAW_SHARED_VISION_PROGRAM.get(NO_WORLD_TO_CLIP=1))            
            glBindTextureUnit(0, self._line_texture)

            glStencilOp(GL_KEEP, GL_KEEP, GL_INCR)
            glBindVertexArray(viewport.get_dummy_vao())

            # Increment the value by one for each draw call thats occluded
            for i, player in enumerate(self.players):

                # Only accept pixels which were previously covered
                glStencilFunc(GL_EQUAL, i, 0xFF)

                depth = 1.0 - (i + 1) / (len(self.players) + 1)
                glUniform3f(0, player[0], player[1], depth)
                glDrawArrays(GL_TRIANGLES, 0, self.num_lines * 9)
            
            glDepthMask(GL_TRUE)

        # FOW write back to history
        with self._fow_history_fb.bind():
            # Update any new pixels which arent occluded by all players
            # and use the setting of depth=0 to filer excessive writes
            glUseProgram(self._draw_fow_history_program)
            glStencilFunc(GL_NOTEQUAL, len(self.players), 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            self.triangle_screen.draw()


        # Per character shared visibility
        # Framebuffer really isnt needed here, could just draw directly the GL_BACK
        # it should use the FOW grid in some mildly intelligent way to account for previously seen areas
        glViewport(0, 0, wnd.width, wnd.height)
        with self._shared_vis_fb.bind():

            # Draw occlusion
            glStencilMask(0xFF)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

            # Don't write to colour or depth
            glDepthMask(GL_FALSE)
            glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)

            glUseProgram(_DRAW_SHARED_VISION_PROGRAM.get(NO_WORLD_TO_CLIP=1))

            # glStencilFunc(GL_ALWAYS, 1, 0xFF)
            # glStencilOp(GL_KEEP, GL_KEEP, GL_INCR)

            glBindTextureUnit(0, self._line_texture)
            glBindVertexArray(viewport.get_dummy_vao())
            
            # Increment on stencil + depth pass
            # We could disable depth testing here.
            glStencilOp(GL_KEEP, GL_KEEP, GL_INCR)

            # Increment the value by one for each draw call thats occluded
            for i, player in enumerate(self.players):

                # Only accept pixels which were previously covered
                glStencilFunc(GL_EQUAL, i, 0xFF)

                depth = 1.0 - (i + 1) / (len(self.players) + 1)
                glUniform3f(0, player[0], player[1], depth)
                glDrawArrays(GL_TRIANGLES, 0, self.num_lines * 9)


            # Renable colour + depth writeback
            glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
            glDepthMask(GL_TRUE)

            # Only draw things not occluded by all players
            # Draw texture version (so we can see the FOW texture array)
            if True:
                glUseProgram(self._draw_texture_program)
                glBindTextureUnit(0, self._fow_history_fb_col.value)
            # Draw solid col
            else:
                glUseProgram(self._draw_shape_program)
                glUniform4f(1, 0, 1, 0, 1)
            glStencilFunc(GL_NOTEQUAL, len(self.players), 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glUniform1f(0, 0)
            self.triangle_screen.draw()


            if(self._draw_lines):
                glStencilFunc(GL_ALWAYS, 0, 0xFF)
                glDepthMask(GL_FALSE)
                glUseProgram(_DRAW_LINES_PROGRAM.get(NO_WORLD_TO_CLIP=1))
                glBindVertexArray(viewport.get_dummy_vao())
                glBindTextureUnit(0, self._line_texture)
                glUniform3f(0, 0.0, 0.0, 0.0)
                glDrawArrays(GL_LINES, 0, self.num_lines * 2)
                glDepthMask(GL_TRUE)


        # Copy to back
        self._shared_vis_fb.blit_to_back(wnd.width, wnd.height, GL_COLOR_BUFFER_BIT, GL_NEAREST)

        # Test to see fow
        # self._fow_history_fb.blit_to_back(wnd.width, wnd.height, GL_COLOR_BUFFER_BIT, GL_NEAREST)
        

        self.timer_overlay.update(wnd.width, wnd.height)
        wnd.redraw()



    def _resize(self, wnd, width, height):
        self._shared_vis_fb.resize(width, height)
        glViewport(0, 0, width, height)


    def _keypress(self, wnd, key, x, y):
        # Move the camera
        shift = key.isupper()
        key = key.lower()

        if key == b'w':
            self._fow_debug_offset[1] += 0.01
        elif key == b'a':
            self._fow_debug_offset[0] -= 0.01
        elif key == b's':
            self._fow_debug_offset[1] -= 0.01
        elif key == b'd':
            self._fow_debug_offset[0] += 0.01
        
        elif key == b'l':
            self._draw_lines = not self._draw_lines

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # No redraw
        else:
            return

        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()




