from math import cos, sin, pi

import numpy
import random

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
readonly layout(std430, binding = 0) buffer lines_ { vec4 lines[];};
readonly layout(std430, binding = 1) buffer pointLightPositions_ { vec4 pointLightPositions[];};


flat layout(location = 0) out vec4 lineData;
layout(location = 1) out float direction;
layout(location = 2) out vec2 imageUv;


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

    imageUv = vec2(
        (lineSide == 0) ? polarPositions.x : polarPositions.y, // Swap between A and B points
        (0.5 + float(pointLightID)) * invTextureHeight
    );
    lineData = ((lineSide == 0) ? line.xyzw : line.zwxy);      // Swap between A and B points
    direction = UV2NDA(imageUv.x);

    gl_Position = vec4(UV2NDA(imageUv), 0.0, 1.0);
}

"""


LINE_SHADOW_FRAGMENT_SHADER_SOURCE = """
#version 460 core

#define TWOPI 6.283185307179586476925286766559


// Depth peel settings
layout(location = 2) uniform uint doDepthPeel = 0;
layout(binding = 2) uniform sampler2D pointLightLineMap;


flat layout(location = 0) in vec4 lineData;
layout(location = 1) in float direction;
layout(location = 2) in vec2 imageUv;


layout(location = 0) out vec4 nearestLine;


void main()
{

    if(doDepthPeel == 1)
    {
        if(textureLod(pointLightLineMap, imageUv, 0) == lineData) { discard; }
    }

    nearestLine = lineData;

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
    uv = 2.0 * vec2(
        float(gl_VertexID % 2),
        float(gl_VertexID / 2)
    ) - 1.0;

    gl_Position = vec4(uv, 0.0, 1.0);
}
"""


DRAW_LIGHT_ACCUM_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform uint pointLightCount;

layout(binding = 0) uniform sampler2D pointLightLineMap;
layout(binding = 1) uniform sampler2D pointLightShadowMap;
layout(binding = 2) uniform sampler2D pointLightLineMapPeel;   // these are only used if we're trying some crappy penumbra
layout(binding = 3) uniform sampler2D pointLightShadowMapPeel;
readonly layout(std430, binding = 4) buffer pointLightPositions_ { vec4 pointLightPositions[];};
readonly layout(std430, binding = 5) buffer pointLightColRads_ { vec4 pointLightColRads[];};

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outRgba;

#define INV2PI 0.15915494309189533576888376337251436203445964574
#define TWOPI 6.283185307179586476925286766559
#define EPSILON 1e-7

// Penumbra will cause artefacts regarding bleeding through
// connected lines, currently I haven't got a good way to handle
// this
// #define DO_PENUMBRA

#define uvToAngle(localisedUv) atan(localisedUv.y, localisedUv.x) * INV2PI


const vec2 textureSize = vec2(textureSize(pointLightLineMap, 0));
const vec2 invTextureSize = 1.0 / textureSize;


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


// Rather than sampling the shadowmap as a shadowmap, we generate line segments, based upon the distance
// and construct a new temporary line with which we can perform line-line intersection tests
bool calcShadowMapOcclusion(
    const vec2 localUv,
    const sampler2D shadowMap,
    const float X,
    const float Y
) {

    float nearestAngleSegment = round(X * textureSize.x) * invTextureSize.x;

    float Da = 1.0 / (1.0 - textureLod(shadowMap, vec2(nearestAngleSegment - invTextureSize.x, Y), 0).r) - 1.0;
    vec2 pA = Da * vec2(
        cos(TWOPI * (nearestAngleSegment - invTextureSize.x)),
        sin(TWOPI * (nearestAngleSegment - invTextureSize.x))
    );
    float Db = 1.0 / (1.0 - textureLod(shadowMap, vec2(nearestAngleSegment, Y), 0).r) - 1.0;
    vec2 pB = Db * vec2(
        cos(TWOPI * (nearestAngleSegment)),
        sin(TWOPI * (nearestAngleSegment))
    );
    float Dc = 1.0 / (1.0 - textureLod(shadowMap, vec2(nearestAngleSegment + invTextureSize.x, Y), 0).r) - 1.0;
    vec2 pC = Dc * vec2(
        cos(TWOPI * (nearestAngleSegment + invTextureSize.x)),
        sin(TWOPI * (nearestAngleSegment + invTextureSize.x))
    );

    return linesIntersecting(localUv, vec4(pA, pB)) || linesIntersecting(localUv, vec4(pB, pC));
}


void main()
{

    vec3 totalAccum = vec3(0.0);

    for(uint pointLightID=0; pointLightID<pointLightCount; ++pointLightID)
    {
        
        const vec2 localUv = uv - pointLightPositions[pointLightID].xy;
        const vec4 colRad = pointLightColRads[pointLightID];

        const float dist = length(localUv);

        if(dist >= colRad.w) { continue; } // skip fragments that can't be lit

        float attenuation = 1.0 / (1.0 + dist);

        const float X = uvToAngle(localUv);
        const float Y = (0.5 + float(pointLightID)) * invTextureSize.y;
        const float Z = 1.0 - attenuation;

        // line intersections + shadow map
        const vec4 angleLine1 = textureLod(pointLightLineMap, vec2(X - invTextureSize.x, Y), 0);
        const vec4 angleLine2 = textureLod(pointLightLineMap, vec2(X, Y), 0);
        const vec4 angleLine3 = textureLod(pointLightLineMap, vec2(X + invTextureSize.x, Y), 0);

        bool occluded = (

            // Linemap tests
            linesIntersecting(localUv, angleLine1) || linesIntersecting(localUv, angleLine2) || linesIntersecting(localUv, angleLine3)
            
            // Shadow map tests
            // Prevents light leaks where the nearest line for an angle sector actually doesn't cross the
            // line from the current coord to the light.
            || calcShadowMapOcclusion(localUv, pointLightShadowMap, X, Y)
        );

        #ifdef DO_PENUMBRA
            const float R = 1.0;

            // Do penumbra stuff
            // https://www.geogebra.org/calculator/cye3v4fe
            // We're totally ignoring the falloff you'd expect for anything
            // that isn't in shadow, as this would require use to do some clever
            // or sample a bunch of times.
            // TODO: Look into the above.
            if(occluded && R != 0.0)
            {

                vec2 Ld = normalize(angleLine1.xy - angleLine1.zw);
                vec2 LaInner = normalize(angleLine1.xy - Ld * R);
                vec2 LaOuter = normalize(angleLine1.xy);
                vec2 LbInner = normalize(angleLine1.zw + Ld * R);
                vec2 LbOuter = normalize(angleLine1.zw);

                float LaShadowing = max(
                    0,
                    1 - (
                        (1 - dot(normalize(localUv - angleLine1.xy), LaOuter))
                        / (1 - dot(LaInner, LaOuter))
                    )
                );
                float LbShadowing = max(
                    0,
                    1 - (
                        (1 - dot(normalize(localUv - angleLine1.zw), LbOuter))
                        / (1 - dot(LbInner, LbOuter))
                    )
                );

                Ld = normalize(angleLine2.xy - angleLine2.zw);
                LaInner = normalize(angleLine2.xy - Ld * R);
                LaOuter = normalize(angleLine2.xy);
                LbInner = normalize(angleLine2.zw + Ld * R);
                LbOuter = normalize(angleLine2.zw);

                LaShadowing = max(
                    LaShadowing,
                    1 - (
                        (1 - dot(normalize(localUv - angleLine2.xy), LaOuter))
                        / (1 - dot(LaInner, LaOuter))
                    )
                );
                LbShadowing = max(
                    LaShadowing,
                    1 - (
                        (1 - dot(normalize(localUv - angleLine2.zw), LbOuter))
                        / (1 - dot(LbInner, LbOuter))
                    )
                );

                Ld = normalize(angleLine3.xy - angleLine3.zw);
                LaInner = normalize(angleLine3.xy - Ld * R);
                LaOuter = normalize(angleLine3.xy);
                LbInner = normalize(angleLine3.zw + Ld * R);
                LbOuter = normalize(angleLine3.zw);

                LaShadowing = max(
                    LaShadowing,
                    1 - (
                        (1 - dot(normalize(localUv - angleLine3.xy), LaOuter))
                        / (1 - dot(LaInner, LaOuter))
                    )
                );
                LbShadowing = max(
                    LaShadowing,
                    1 - (
                        (1 - dot(normalize(localUv - angleLine3.zw), LbOuter))
                        / (1 - dot(LbInner, LbOuter))
                    )
                );

                attenuation *= max(LaShadowing, LbShadowing);

                // At certain extreme angles, the attenuation can get all freaky, in such cases, the simplest thing
                // is to simply zero it.
                attenuation *= float(attenuation <= 1.0 && attenuation >= 0.0);

                // Test the peel maps for occlusions if the attenuation isn't zero
                if(attenuation > 0.0)
                {

                    occluded = (
                        linesIntersecting(localUv, textureLod(pointLightLineMapPeel, vec2(X - invTextureSize.x, Y), 0))
                        || linesIntersecting(localUv, textureLod(pointLightLineMapPeel, vec2(X, Y), 0))
                        || linesIntersecting(localUv, textureLod(pointLightLineMapPeel, vec2(X + invTextureSize.x, Y), 0))
                        || calcShadowMapOcclusion(localUv, pointLightShadowMapPeel, X, Y)
                    );


                    // Finally, ensure we aren't bleeding through a corner etc
                    if(!occluded)
                    {



                    }

                }

            }

        #endif

        // https://www.geogebra.org/m/rrnjxsbh
        attenuation = pow(
            pow(attenuation, 8.0/colRad.w)
            * (colRad.w - dist)/colRad.w
            * float(dist < colRad.w
            ),
            1.0/1.2
        );

        attenuation *= 1.0 - (1.0 - attenuation) * 0.055;
        totalAccum += colRad.xyz * float(!occluded) * attenuation;
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


LINEMAP_RESOLUTION = 512


class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress
        self.window.on_idle = lambda x: x.redraw()

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

        # Base
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
        self._point_lights_linemap = viewport.FramebufferTarget(
            GL_RGBA32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                GL_TEXTURE_MAG_FILTER: GL_NEAREST,
            }
        );
        self._point_light_shadow_framebuffer = viewport.Framebuffer(
            (self._point_lights_linemap, self._point_light_shadow_depth,),
            LINEMAP_RESOLUTION,    # resolution of 512
            256     # support 256 pointlights
        )

        # Peel
        self._point_light_shadow_depth_peel = viewport.FramebufferTarget(
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
        self._point_lights_linemap_peel = viewport.FramebufferTarget(
            GL_RGBA32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                GL_TEXTURE_MAG_FILTER: GL_NEAREST,
            }
        );
        self._point_light_shadow_framebuffer_peel = viewport.Framebuffer(
            (self._point_lights_linemap_peel, self._point_light_shadow_depth_peel,),
            LINEMAP_RESOLUTION,    # resolution of 512
            256     # support 256 pointlights
        )

        self._vao_ptr = ctypes.c_int()
        self._buffers_ptr = (ctypes.c_int * 3)()

        glCreateBuffers(3, self._buffers_ptr)
        glCreateVertexArrays(1, self._vao_ptr)

        self._dummy_vao = self._vao_ptr.value

        self._lines = self._buffers_ptr[0]
        self._point_lights_pos = self._buffers_ptr[1]
        self._point_lights_colrads = self._buffers_ptr[2]

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
        ], dtype=numpy.float32) * 0.125).tobytes()

        # 10
        lines_data += (numpy.array([
            -1.0, -1.0, -1.0, 0.5,
            -1.0, -1.0, 1.0, -1.1,
            1.0, 1.0, -0.5, 1.0,
            0.5, 0.5, 1.0, -0.5,
            -0.317080949074, 0.1788264608952, -0.1824981088947, 0.292159378941,
        ], dtype=numpy.float32) * 0.25).tobytes()

        # 15
        lines_data += (numpy.array([
            -1.0, -1.0, -1.0, 0.5,
            -1.0, -1.0, 1.0, -1.1,
            1.0, 1.0, -0.5, 1.0,
            0.5, 0.5, 1.0, -0.5,
            -0.317080949074, 0.1788264608952, -0.1824981088947, 0.292159378941,
        ], dtype=numpy.float32) * 0.325).tobytes()

        # 20
        lines_data += (numpy.array([
            -1.0, -1.0, -1.0, 0.5,
            -1.0, -1.0, 1.0, -1.1,
            1.0, 1.0, -0.5, 1.0,
            0.5, 0.5, 1.0, -0.5,
            -0.317080949074, 0.1788264608952, -0.1824981088947, 0.292159378941,
        ], dtype=numpy.float32) * 0.5).tobytes()

        # 25
        lines_data += (numpy.array([
            -1.0, -1.0, -1.0, 0.5,
            -1.0, -1.0, 1.0, -1.1,
            1.0, 1.0, -0.5, 1.0,
            0.5, 0.5, 1.0, -0.5,
            -0.317080949074, 0.1788264608952, -0.1824981088947, 0.292159378941,
        ], dtype=numpy.float32) * 0.625).tobytes()

        # 30
        lines_data += (numpy.array([
            -1.0, -1.0, -1.0, 0.5,
            -1.0, -1.0, 1.0, -1.1,
            1.0, 1.0, -0.5, 1.0,
            0.5, 0.5, 1.0, -0.5,
            -0.317080949074, 0.1788264608952, -0.1824981088947, 0.292159378941,
        ], dtype=numpy.float32) * 0.75).tobytes()


        # 100 point lights
        point_lights_data = (numpy.array([
            [(x+0.5)*0.1, (y+0.5)*0.1,     0.0, 0.0   ]
            # [0, 0,     0.0, 0.0   ]
            for x in range(-5, 5)
            for y in range(-5, 5)
        ], dtype=numpy.float32) * 1.0)

        point_lights_colrads_data = numpy.array([
            # [random.random(), random.random(), random.random(), random.random()*0.5]
            [1.0, 1.0, 1.0, 1.0]
            for _ in point_lights_data
        ], dtype=numpy.float32).tobytes()

        point_lights_data = point_lights_data.tobytes()

        glNamedBufferStorage(self._lines, len(lines_data), lines_data, 0)
        glNamedBufferStorage(self._point_lights_pos, len(point_lights_data), point_lights_data, 0)
        glNamedBufferStorage(self._point_lights_colrads, len(point_lights_colrads_data), point_lights_colrads_data, 0)

        # Do an initial setup of the shadow maps
        self._recalculate_point_lights_shadows()

        glViewport(0, 0, wnd.width, wnd.height)

    def _recalculate_point_lights_shadows(self, idx=None):
        previous_viewport = glGetIntegerv(GL_VIEWPORT)

        glViewport(0, 0, LINEMAP_RESOLUTION, 256)
        glUseProgram(self._draw_line_shadows_program)

        glUniform1f(0, 1.0 / 256.0)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._lines)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._point_lights_pos)
        glBindVertexArray(self._dummy_vao)

        # Base
        glUniform1ui(2, 0)
        with self._point_light_shadow_framebuffer.bind():
            # If idx is None, recalculate everything
            if idx is None:
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                glDrawArraysInstanced(
                    GL_LINES,
                    0,
                    2 * 30,   # 2 * lineCount
                    2 * 100, # 2 * pointLightCount
                )
            # Recaculate just one point light
            else:
                glEnable(GL_SCISSOR_TEST)
                glScissor(0, idx, LINEMAP_RESOLUTION, 1);
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                glDisable(GL_SCISSOR_TEST)
                glUniform1ui(1, idx)
                glDrawArraysInstanced(
                    GL_LINES,
                    0,
                    2 * 30,   # 2 * lineCount
                    2 * 1,   # 2 * pointLightCount
                )

        # Peel
        glUniform1ui(2, 1)
        glBindTextureUnit(2, self._point_lights_linemap.texture)
        with self._point_light_shadow_framebuffer_peel.bind():
            # If idx is None, recalculate everything
            if idx is None:
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                glDrawArraysInstanced(
                    GL_LINES,
                    0,
                    2 * 30,   # 2 * lineCount
                    2 * 100, # 2 * pointLightCount
                )
            # Recaculate just one point light
            else:
                glEnable(GL_SCISSOR_TEST)
                glScissor(0, idx, LINEMAP_RESOLUTION, 1);
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                glDisable(GL_SCISSOR_TEST)
                glUniform1ui(1, idx)
                glDrawArraysInstanced(
                    GL_LINES,
                    0,
                    2 * 30,   # 2 * lineCount
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
        glUniform1ui(0, 1) # point light count, only drawing for now
        glBindTextureUnit(0, self._point_lights_linemap.texture)
        glBindTextureUnit(1, self._point_light_shadow_depth.texture)
        glBindTextureUnit(2, self._point_lights_linemap_peel.texture)
        glBindTextureUnit(3, self._point_light_shadow_depth_peel.texture)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 4, self._point_lights_pos)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 5, self._point_lights_colrads)

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
                2 * 30 # 2 * lineCount
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

        self._recalculate_point_lights_shadows()

        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
