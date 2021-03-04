from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport



LINE_SHADOW_VERTEX_SHADER_SOURCE = """
#version 460 core

#define INV2PI 0.15915494309189533576888376337251436203445964574
#define UV2NDA(x) 2.0 * (x) - 1.0


layout(location = 0) uniform float invTextureHeight;
layout(location = 1) uniform uint startingPointLightID = 0;


// We store the lines in a buffer as floats so we are able to access
// both points of the line at the same time.
// TODO: Test if using a geometry shader works better.
readonly layout(std430, binding = 0) buffer lines_ { vec4 lines[];};
readonly layout(std430, binding = 1) buffer pointLightPositions_ { vec4 pointLightPositions[];};


flat layout(location = 0) out vec4 lineData;
layout(location = 1) out float direction;


void main()
{
    // Lines need to be duplicated so we can effectively wrap around
    // when projected lines aren't simply in the 0->1 range and are in the
    // -1->0 range.
    const float polarOffset = float(gl_InstanceID & 1);
    const uint pointLightID = startingPointLightID + gl_InstanceID >> 1;

    const uint lineId = gl_VertexID >> 1;
    const uint lineSide = gl_VertexID & 1;

    const vec4 light = pointLightPositions[pointLightID];
    vec4 line = lines[lineId] - light.xyxy; // Make sure the line is always relative to the light

    // x = A, y = B
    vec2 polarPositions = atan(line.yw, line.xz) * INV2PI;

    // Make sure the points are the minimum circular distance
    #if 0 // reference

        if(polarPositions.y < polarPositions.x) {
            polarPositions.x -= sign(polarPositions.x) * float(abs(polarPositions.y - polarPositions.x) > 0.5);
        }
        else {
            polarPositions.y -= sign(polarPositions.y) * float(abs(polarPositions.x - polarPositions.y) > 0.5);
        }
    
    #else // branchless

        polarPositions -= (
            vec2(lessThan(polarPositions.yx, polarPositions.xy))
            * sign(polarPositions)
            * vec2(greaterThan(abs(polarPositions - polarPositions.yx), vec2(0.5)))
        );

    #endif

    // In order to make everything airtight (so no holes where lines meet)
    // the lines need to have a consistent winding order, to get around
    // this, we can instead opt to make sure our line coords are sorted.
    if(polarPositions.y < polarPositions.x)
    {
        float tmp = polarPositions.x;
        polarPositions.x = polarPositions.y;
        polarPositions.y = tmp;

        vec2 tmpl = line.xy;
        line.xy = line.zw;
        line.zw = tmpl;
    }

    // Apply wrap-around offset
    polarPositions += polarOffset;

    // Swap between A and B points
    const float X = UV2NDA((lineSide == 0) ? polarPositions.x : polarPositions.y);
    const float Y = UV2NDA((0.5 + float(pointLightID)) * invTextureHeight);

    lineData = ((lineSide == 0) ? line.xyzw : line.zwxy);
    direction = X;

    gl_Position = vec4(X, Y, 0.0, 1.0);
}

"""


LINE_SHADOW_FRAGMENT_SHADER_SOURCE = """
#version 460 core

#define TWOPI 6.283185307179586476925286766559

flat layout(location = 0) in vec4 lineData;
layout(location = 1) in float direction;

void main()
{
    // Calculate the distance from the origin when facing in a direction
    // dictated by the polar coordinates to the target line.
    // https://www.geogebra.org/m/pabfs2c9
    vec2 directionVec = vec2(
        cos(TWOPI*((1.0+direction) * 0.5 - 0.5)),
        sin(TWOPI*((1.0+direction) * 0.5 - 0.5))
    );

    vec2 lineDiff = lineData.zw - lineData.xy;
    float u = (
        (directionVec.x * lineData.y - directionVec.y * lineData.x)
        / (lineDiff.x * directionVec.y - lineDiff.y * directionVec.x)
    );

    vec2 I = lineData.xy + lineDiff * u;
    gl_FragDepth =  1.0 - 1.0 / (1.0 + length(I));
}

"""


DRAW_LIGHT_ACCUM_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) out vec2 uv;

void main()
{
    uv = vec2(
        float(gl_VertexID % 2),
        float(gl_VertexID / 2)
    );

    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}
"""


DRAW_LIGHT_ACCUM_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform uint pointLightCount;

layout(binding = 0) uniform sampler2DShadow pointLightShadowMap;
layout(binding = 0) uniform sampler2D pointLightShadowMapRaw;
readonly layout(std430, binding = 1) buffer pointLightPositions_ { vec4 pointLightPositions[];};

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outRgba;

#define INV2PI 0.15915494309189533576888376337251436203445964574
#define TWOPI 6.283185307179586476925286766559
#define EPSILON 1e-7
#define UV2NDA(x) 2.0 * (x) - 1.0

const vec2 textureSize = vec2(textureSize(pointLightShadowMap, 0));
const vec2 invTextureSize = 1.0 / vec2(textureSize(pointLightShadowMap, 0));


// https://www.geogebra.org/m/ytnhzgzb
bool linesIntersecting(vec2 lineA, vec4 lineB)
{
    if(lineB.xy == lineB.zw) { return false; } // not a line

    vec2 AB = lineA.xy;
    vec2 CD = lineB.xy - lineB.zw;
    vec2 AC = lineA.xy - lineB.xy;

    float d = AB.x * CD.y - AB.y * CD.x;
    float u = sign(d) * (AC.x * AB.y - AC.y * AB.x);
    float t = sign(d) * (AC.x * CD.y - AC.y * CD.x);

    return (min(u, t) >= -EPSILON && max(u, t) < abs(d));
}



void main()
{


    vec3 totalAccum = vec3(0.0);

    for(uint pointLightID=0; pointLightID<pointLightCount; ++pointLightID)
    {
        
        const vec4 pointLightPos = pointLightPositions[pointLightID];
        const vec2 localUv = (2.0 * uv - 1.0) - pointLightPos.xy;
        float attenuation = 1.0 / (1.0 + length(localUv));

        const float X = atan(localUv.y, localUv.x) * INV2PI;
        const float Y = (0.5 + float(pointLightID)) * invTextureSize.y;
        const float Z = 1.0 - attenuation;


        float nearestAngleSegment = round(X * textureSize.x) * invTextureSize.x;


        float Da = 1.0 / (1.0 - textureLod(pointLightShadowMapRaw, vec2(nearestAngleSegment - invTextureSize.x, Y), 0).r) - 1.0;
        vec2 pA = Da * vec2(
            cos(TWOPI * (nearestAngleSegment - invTextureSize.x)),
            sin(TWOPI * (nearestAngleSegment - invTextureSize.x))
        );
        
        float Db = 1.0 / (1.0 - textureLod(pointLightShadowMapRaw, vec2(nearestAngleSegment, Y), 0).r) - 1.0;
        vec2 pB = Db * vec2(
            cos(TWOPI * (nearestAngleSegment)),
            sin(TWOPI * (nearestAngleSegment))
        );

        float Dc = 1.0 / (1.0 - textureLod(pointLightShadowMapRaw, vec2(nearestAngleSegment + invTextureSize.x, Y), 0).r) - 1.0;
        vec2 pC = Dc * vec2(
            cos(TWOPI * (nearestAngleSegment + invTextureSize.x)),
            sin(TWOPI * (nearestAngleSegment + invTextureSize.x))
        );


        bool intersecting = linesIntersecting(localUv, vec4(pA, pB)) || linesIntersecting(localUv, vec4(pB, pC));
        totalAccum += float(!intersecting) * attenuation;

    }

    outRgba = vec4(totalAccum, 1.0);
}

"""


DRAW_LINES_VERTEX_SHADER_SOURCE = """
#version 460 core

#define UV2NDA(x) 2.0 * (x) - 1.0


readonly layout(std430, binding = 0) buffer lines_ { vec4 lines[];};


void main()
{
    const uint lineId = gl_VertexID >> 1;
    const uint lineSide = gl_VertexID & 1;
    vec4 line = lines[lineId];
    vec2 localUv = ((lineSide == 0) ? line.xy : line.zw);
    gl_Position = vec4(localUv, 0.0, 1.0);
}


"""

DRAW_LINES_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) out vec4 outRgba;

void main()
{
    outRgba = vec4(1.0, 0.0, 0.0, 1.0);
}

"""

MOVE_POINT_LIGHT_SHADER_SOURCE = """
#version 460 core

layout(local_size_x=1) in;

layout(std430, binding = 0) buffer pointLightPositions_ { vec4 pointLightPositions[];};
layout(location = 0) uniform uint targetLine;
layout(location = 1) uniform vec2 amount;


void main()
{
    pointLightPositions[targetLine].xy += amount;
}

"""


class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self.draw_lines = True


    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self._draw_line_shadows_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=LINE_SHADOW_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=LINE_SHADOW_FRAGMENT_SHADER_SOURCE,
        )
        self._draw_light_accum_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_LIGHT_ACCUM_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_LIGHT_ACCUM_FRAGMENT_SHADER_SOURCE,
        )
        self._draw_lines_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_LINES_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_LINES_FRAGMENT_SHADER_SOURCE
        )
        self._move_point_light_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=MOVE_POINT_LIGHT_SHADER_SOURCE,
        )

        self._point_light_shadow_depth = viewport.FramebufferTarget(
            GL_DEPTH_COMPONENT32F,
            True,
            # PCF friendly settings
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
                GL_TEXTURE_COMPARE_FUNC: GL_LEQUAL,
                GL_TEXTURE_COMPARE_MODE: GL_COMPARE_REF_TO_TEXTURE,
            }
        )
        self._point_light_shadow_framebuffer = viewport.Framebuffer(
            (self._point_light_shadow_depth,),
            512,    # resolution of 512
            256     # support 256 pointlights
        )

        self._vao_ptr = ctypes.c_int()
        self._buffers_ptr = (ctypes.c_int * 3)()

        glCreateBuffers(3, self._buffers_ptr)
        glCreateVertexArrays(1, self._vao_ptr)

        self._dummy_vao = self._vao_ptr.value

        self._lines = self._buffers_ptr[0]
        self._point_lights_pos = self._buffers_ptr[1]

        # 4 lines
        # # BOX
        # lines_data = (numpy.array([
        #     -1.0, -1.0, -1.0, 1.0,
        #     -1.0, -1.0, 1.0, -1.0,
        #     1.0, 1.0, -1.0, 1.0,
        #     1.0, 1.0, 1.0, -1.0,
        # ], dtype=numpy.float32) * 0.5).tobytes()

        # 5 lines
        lines_data = (numpy.array([
            -1.0, -1.0, -1.0, 0.5,
            -1.0, -1.0, 1.0, -1.1,
            1.0, 1.0, -0.5, 1.0,
            0.5, 0.5, 1.0, -0.5,
            -0.317080949074, 0.1788264608952, -0.1824981088947, 0.292159378941,
        ], dtype=numpy.float32) * 0.5).tobytes()

        # 100 point lights
        point_lights_data = numpy.array([
            [(x+0.5)*0.05, (y+0.5)*0.05,     0.0, 0.0   ]
            # [0, 0,     0.0, 0.0   ]
            for x in range(-5, 5)
            for y in range(-5, 5)
        ], dtype=numpy.float32).tobytes()

        glNamedBufferStorage(self._lines, len(lines_data), lines_data, 0)
        glNamedBufferStorage(self._point_lights_pos, len(point_lights_data), point_lights_data, 0)

        # Do an initial setup of the shadow maps
        self._recalculate_point_lights_shadows()

        glViewport(0, 0, wnd.width, wnd.height)

    def _recalculate_point_lights_shadows(self, idx=None):
        previous_viewport = glGetIntegerv(GL_VIEWPORT)
        with self._point_light_shadow_framebuffer.bind():
            glViewport(0, 0, 512, 256)
            glUseProgram(self._draw_line_shadows_program)

            glUniform1f(0, 1.0 / 256.0)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._lines)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._point_lights_pos)
            glBindVertexArray(self._dummy_vao)

            # If idx is None, recalculate everything
            if idx is None:
                glClear(GL_DEPTH_BUFFER_BIT)
                glDrawArraysInstanced(
                    GL_LINES,
                    0,
                    2 * 5,   # 2 * lineCount
                    2 * 100, # 2 * pointLightCount
                )

            # Recaculate just one point light
            else:
                glEnable(GL_SCISSOR_TEST)
                glScissor(0, idx, 512, 1);
                glClear(GL_DEPTH_BUFFER_BIT)
                glDisable(GL_SCISSOR_TEST)
                glUniform1ui(1, idx)
                glDrawArraysInstanced(
                    GL_LINES,
                    0,
                    2 * 5,   # 2 * lineCount
                    2 * 1,   # 2 * pointLightCount
                )

        glViewport(
            previous_viewport[0],
            previous_viewport[1],
            previous_viewport[2],
            previous_viewport[3]
        )

    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self._draw_light_accum_program)
        glBindTextureUnit(0, self. _point_light_shadow_depth.texture)
        glUniform1ui(0, 1) # point light count, only drawing for now
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._point_lights_pos)

        glBindVertexArray(self._dummy_vao)
        glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glDepthMask(GL_TRUE)
        glEnable(GL_DEPTH_TEST)

        if self.draw_lines:
            glUseProgram(self._draw_lines_program)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._lines)
            glDrawArrays(
                GL_LINES,
                0,
                2 * 5 # 2 * lineCount
            )

    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        # Toggle line drawing
        if key == b'l':
            self.draw_lines = not self.draw_lines
        # Dont do anything
        else:
            return
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height

        # Move the first point light around
        glUseProgram(self._move_point_light_program)
        glUniform1ui(0, 0)
        glUniform2f(1, deriv_u * 2.0, -deriv_v * 2.0)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._point_lights_pos)
        glDispatchCompute(1, 1, 1)
        glMemoryBarrier(GL_COMMAND_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        self._recalculate_point_lights_shadows(0)

        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
