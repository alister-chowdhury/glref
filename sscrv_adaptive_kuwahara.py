"""
Screen space curvature (for a lack of a better name).

The main purpose of this, is it helps "enchance" convex and concave regions
of a model considerably better than SSAO by a means of appoximating curvature.

It has the additional benefit that it only requires a depth pass (or view space
positions).

The down side is normals are implicitly smoothed or hardend based upon the
radius.

This is very similar to SSAO but differs in the following ways:
    1. The hemisphere pointing to the camera is used, rather than the
       surface normal.
    2. The final occlusion starts of as mid occluded, rather than fully
       occluded or fully visible.
    3. When a sample is infront of the reference position the visibility
       is decreased, when it is behind it is increased.

"""
from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport


DRAW_N_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;

void main() {
    gl_Position = modelViewProjection * vec4(P, 1.0);
}
"""


FULLSCREEN_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) out vec2 outUv;

void main() {

    outUv = vec2(
        float(gl_VertexID) - 0.5,
        float(gl_VertexID & 1) * 2.0
    );
    gl_Position = vec4(2.0 * outUv - 1.0, 0, 1);
}
"""

SSCRV_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 inverseProjection;
layout(location = 1) uniform mat4 projection;

layout(binding = 0) uniform sampler2D depthPass;

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outRgba;


// This should really be calculated based upon the scale of the scene.
// or configured manually.
#define RADIUS 0.1

// Samples to us
#ifndef SAMPLES_COUNT
#   define SAMPLES_COUNT 32
#endif


// Vectors which more-or-less evenly sample the hemisphere of (0, 0, 1)
const vec3 HEMISPHERE_VECTORS[SAMPLES_COUNT] = vec3[SAMPLES_COUNT]
(
#if SAMPLES_COUNT == 8
    vec3(0.998866, 0.000000, 0.047619),
    vec3(-0.727056, 0.666042, 0.166667),
    vec3(0.083781, -0.954645, 0.285714),
    vec3(0.556370, 0.725686, 0.404762),
    vec3(-0.838814, -0.148374, 0.523810),
    vec3(0.646305, -0.411126, 0.642857),
    vec3(-0.168143, 0.625483, 0.761905),
    vec3(-0.218103, -0.419945, 0.880952)

#elif SAMPLES_COUNT == 16
    vec3(0.998866, 0.000000, 0.047619),
    vec3(-0.733124, 0.671602, 0.107143),
    vec3(0.086203, -0.982238, 0.166667),
    vec3(0.592670, 0.773033, 0.226190),
    vec3(-0.943666, -0.166921, 0.285714),
    vec3(0.791877, -0.503727, 0.345238),
    vec3(-0.237388, 0.883071, 0.404762),
    vec3(-0.408219, -0.786000, 0.464286),
    vec3(0.800147, 0.292212, 0.523810),
    vec3(-0.750784, 0.309913, 0.583333),
    vec3(0.324660, -0.693780, 0.642857),
    vec3(0.213031, 0.679175, 0.702381),
    vec3(-0.560388, -0.324756, 0.761905),
    vec3(0.557009, -0.122457, 0.821429),
    vec3(-0.272154, 0.387111, 0.880952),
    vec3(-0.043676, -0.337042, 0.940476)

#elif SAMPLES_COUNT == 32
    vec3(0.998866, 0.000000, 0.047619),
    vec3(-0.735158, 0.673465, 0.077381),
    vec3(0.086922, -0.990437, 0.107143),
    vec3(0.602710, 0.786128, 0.136905),
    vec3(-0.970941, -0.171746, 0.166667),
    vec3(0.827317, -0.526272, 0.196429),
    vec3(-0.252876, 0.940687, 0.226190),
    vec3(-0.445554, -0.857887, 0.255952),
    vec3(0.900166, 0.328739, 0.285714),
    vec3(-0.877142, 0.362072, 0.315476),
    vec3(0.397786, -0.850045, 0.345238),
    vec3(0.277444, 0.884534, 0.375000),
    vec3(-0.791168, -0.458498, 0.404762),
    vec3(0.879653, -0.193389, 0.434524),
    vec3(-0.509384, 0.724546, 0.464286),
    vec3(-0.111732, -0.862226, 0.494048),
    vec3(0.651355, 0.548963, 0.523810),
    vec3(-0.832091, 0.034410, 0.553571),
    vec3(0.575735, -0.572933, 0.583333),
    vec3(-0.036492, 0.789166, 0.613095),
    vec3(-0.490774, -0.588112, 0.642857),
    vec3(0.733380, 0.098675, 0.672619),
    vec3(-0.584288, 0.406532, 0.702381),
    vec3(0.149500, -0.664542, 0.732143),
    vec3(0.322019, 0.561965, 0.761905),
    vec3(-0.582051, -0.185690, 0.791667),
    vec3(0.517724, -0.239201, 0.821429),
    vec3(-0.202627, 0.484166, 0.851190),
    vec3(-0.160157, -0.445278, 0.880952),
    vec3(0.365616, 0.192157, 0.910714),
    vec3(-0.328634, 0.086627, 0.940476),
    vec3(0.130965, -0.203681, 0.970238)
#else
#   error "Bad sample count!"

#endif
);


void main() {

    outRgba = vec4(1);

    // Depth-pass -> view-space position
    float depth = texture(depthPass, uv).x;
    vec4 position = inverseProjection * vec4(2.0 * uv - 1.0, depth, 1.0);
       position /= position.w;

    if (position.w <= 0) { return; }

    mat3 TBN;
    {
        // We use the direction to the camera as our normal
        // rather than a surface normal (i.e SSAO)
        vec3 N = -normalize(position.xyz);

        // Frisvad + Pixar Orthonormal Basis
        // https://graphics.pixar.com/library/OrthonormalB/paper.pdf
        const float a  = -1.0 / (sign(N.z) + N.z);
        const float b  = N.x * N.y * a;
        const vec3  T  = vec3(1.0 + sign(N.z) * N.x * N.x * a,
                              sign(N.z) * b,
                              -sign(N.z) * N.x);
        const vec3  B  = vec3(b,
                              sign(N.z) + N.y * N.y * a,
                              -N.y);
        TBN = mat3(T, B, N);

        // Pre-rotate our matrix on the Z axis, by a random amount per-pixel.
        // This prevents visible banding that results from the the hemisphere vectors
        // probing the same directions
        // Random Function : https://www.shadertoy.com/view/Xt23Ry
        float theta = 6.28318530718 * fract(sin(dot(uv, vec2(12.9898,78.233))) * 43758.5453);
        float ca = cos(theta);
        float sa = sin(theta);

        mat3 Rm = mat3(
            vec3(ca, sa, 0.0),
            vec3(-sa, ca, 0.0),
            vec3(0.0, 0.0, 1.0)
        );

        TBN = TBN * Rm;
    }

    // For each orientated hemisphere vector:
    // 1. Offset the position by some radius in that direction.
    // 2. Calculate the UV coordinates they would correspond too
    //    on the depth pass.
    // 3. Sample the depth pass and determine if the point is behind
    //    or infront of the offseted position.
    // 4. If it is in-front mark that decrease the visibility
    //    otherwise increase it.

    float visibility = SAMPLES_COUNT;

    for (uint i = 0; i < SAMPLES_COUNT; ++i) {
        vec3 projNormal = TBN * HEMISPHERE_VECTORS[i];
        vec3 projPosition = position.xyz + projNormal * RADIUS;

        vec4 sampleUv      = projection * vec4(projPosition, 1.0);
             sampleUv.xyz /= sampleUv.w;
             sampleUv.xy   = sampleUv.xy * 0.5 + 0.5;

        float compareDepth = texture(depthPass, sampleUv.xy).x;
        
        // When there is nothing to sample in a region, we adjust the visibility
        // to bias the convexity, the reason for this is to combat the rather
        // distracting haloing that seems to be visible.
        // When attempting to only keep track of which samples pass the test,
        // the result ends up being a bit noisey and rubbish
        if(!(compareDepth > 0 && compareDepth < 1))
        {
            visibility += 0.5;
            continue;
        }

        vec4 comparePosition = inverseProjection * vec4(2.0 * sampleUv.xy - 1.0, compareDepth, 1.0);
        comparePosition /= comparePosition.w;

        float occluded = float(projPosition.z < comparePosition.z);
        occluded *= 2;
        occluded -= 1;

        // Attenuate the influence of the occlusion by the distance in viewspace depth
        // from the original position and sampled position.
        // (This seems to yield less haloing artefacts than distance or using projPosition).
        float attenuation = smoothstep(0,
                                       1,
                                       RADIUS / abs(position.z - comparePosition.z));

        visibility -= occluded * attenuation;
    }

    visibility /= SAMPLES_COUNT * 2;
    outRgba = vec4(visibility);
}

"""


ADPT_KUWAHARA_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(binding = 0) uniform sampler2D renderTarget;

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outRgba;


// Hard coded with a max depth of 3
// 1 = 3x3 grid with 2x2 window
// 2 = 5x5 grid with 3x3 window
// 3 = 7x7 grid with 4x4 window
// etc etc

#define MAX_GRID_DIM_SIZE   (2*3 + 1)
#define MIDDLE_INDEX        ((MAX_GRID_DIM_SIZE * MAX_GRID_DIM_SIZE) / 2)


float samples[MAX_GRID_DIM_SIZE * MAX_GRID_DIM_SIZE];


float sqr(float x) { return x*x; }


vec2 meanAndStd(int qx, int qy)
{
    // Startup of with a depth of 1
    float summed =   samples[MIDDLE_INDEX]                                  // 0,   0
                   + samples[MIDDLE_INDEX + qx]                             // qx,  0
                   + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy) + qx]    // qx, qy
                   + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy)]         // 0,  qy
                   ;

    vec2 meanStdD1;
    meanStdD1.x = summed / 4;
    meanStdD1.y =    sqr(samples[MIDDLE_INDEX] - meanStdD1.x)
                   + sqr(samples[MIDDLE_INDEX + qx] - meanStdD1.x)
                   + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy) + qx] - meanStdD1.x)
                   + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy)] - meanStdD1.x)
                   ;

    summed +=  samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*0]     // 0,   2qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*1]     // qx,  2qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*2]     // 2qx, 2qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*1) + qx*2]     // 2qx, qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*0) + qx*2]     // 2qx, 0
             ;

    vec2 meanStdD2 = meanStdD1;
    meanStdD2.x = summed / 9;
    meanStdD2.y +=  sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*0] - meanStdD2.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*1] - meanStdD2.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*2] - meanStdD2.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*1) + qx*2] - meanStdD2.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*0) + qx*2] - meanStdD2.x)
                  ;

    // If smaller window is smaller return it and don't bother with the
    // third level.
    if(meanStdD2.y/9 > meanStdD1.y/4)
    {
        meanStdD1.y /= 4;
        return meanStdD1;
    }

    summed +=  samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*0]     // 0,   3qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*1]     // qx,  3qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*2]     // 2qx, 3qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*3]     // 3qx, 3qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*3]     // 3qx, 2qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*1) + qx*3]     // 3qx, 1qy
             + samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*0) + qx*3]     // 3qx, 0
             ;

    vec2 meanStdD3 = meanStdD2;
    meanStdD3.x = summed / 16;
    meanStdD3.y +=  sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*0] - meanStdD3.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*1] - meanStdD3.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*2] - meanStdD3.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*3) + qx*3] - meanStdD3.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*2) + qx*3] - meanStdD3.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*1) + qx*3] - meanStdD3.x)
                  + sqr(samples[MIDDLE_INDEX + (MAX_GRID_DIM_SIZE*qy*0) + qx*3] - meanStdD3.x)
                  ;

    meanStdD2.y /= 9;
    meanStdD3.y /= 16;
    if(meanStdD2.y < meanStdD3.y)
    {
        return meanStdD2;
    }
    return meanStdD3;
}


void main() {

    // Up front fetch the samples
    int pixOffset = -MAX_GRID_DIM_SIZE/2;
    vec2 pixelSize = fwidthCoarse(uv) * 1.41421356237; // Scaling the pixel size
                                                       // allows for a visually nicer
                                                       // dithering-like pattern

    for(int Y=0; Y<MAX_GRID_DIM_SIZE; ++Y)
    {
        for(int X=0; X<MAX_GRID_DIM_SIZE; ++X)
        {
            samples[Y*MAX_GRID_DIM_SIZE + X] = texture(renderTarget, uv + vec2(float(X + pixOffset), float(Y + pixOffset)) * pixelSize ).x;
        }
    }

    vec2 meanStdQ1 = meanAndStd(-1, -1);
    vec2 meanStdQ2 = meanAndStd(1, -1);
    vec2 meanStdQ3 = meanAndStd(1, 1);
    vec2 meanStdQ4 = meanAndStd(-1, 1);

    vec2 target = meanStdQ1;
    if(meanStdQ2.y < target.y)
    {
        target = meanStdQ2;
    }
    if(meanStdQ3.y < target.y)
    {
        target = meanStdQ3;
    }
    if(meanStdQ4.y < target.y)
    {
        target = meanStdQ4;
    }

    outRgba = vec4(target.x);
}

"""


class Renderer(object):


    def __init__(self):

        self.window = viewport.Window()
        self.camera = viewport.Camera()

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self.main_geom = None
        self._option = 0

    def run(self):
        self.window.run()

    def _init(self, wnd):
        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glDisable(GL_CULL_FACE)


        self.main_geom = viewport.load_obj(
            # "data/cubeWithNormals.obj",
            "data/armadillo.obj",
            (
                viewport.ObjGeomAttr.P,
            )
        )

        self._main_geom_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1.5, 0, 1],
        ], dtype=numpy.float32)


        self._draw_depth_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_N_VERTEX_SHADER_SOURCE,
        )

        self._sscrv_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=FULLSCREEN_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=SSCRV_FRAGMENT_SHADER_SOURCE
        )

        self._adpt_kuwahara_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=FULLSCREEN_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=ADPT_KUWAHARA_FRAGMENT_SHADER_SOURCE
        )

        self._framebuffer_depth = viewport.FramebufferTarget(
            GL_DEPTH32F_STENCIL8,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )
        self._framebuffer = viewport.Framebuffer(
            (self._framebuffer_depth,),
            wnd.width,
            wnd.height
        )

        # Second framebuffer so we can see things with renderdoc
        self._framebuffer2_col = viewport.FramebufferTarget(
            GL_RGB32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )
        self._framebuffer2_depth = viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True)
        self._framebuffer2 = viewport.Framebuffer(
            (self._framebuffer2_col, self._framebuffer2_depth),
            wnd.width,
            wnd.height
        )

        self._framebuffer3_col = viewport.FramebufferTarget(GL_RGB32F, True)
        self._framebuffer3_depth = viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True)
        self._framebuffer3 = viewport.Framebuffer(
            (self._framebuffer3_col, self._framebuffer3_depth),
            wnd.width,
            wnd.height
        )

        self.camera.look_at(
            numpy.array([0, 3, 0]),
            numpy.array([0.83922848, 3.71858291, 0.52119542]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):
        # Draw stencil-depth
        with self._framebuffer.bind():
            glStencilFunc(GL_ALWAYS, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
            glStencilMask(0xFF)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

            glUseProgram(self._draw_depth_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, (self._main_geom_model * self.camera.view_projection).flatten())
            self.main_geom.draw()

        # Akward GL gubbins + me not bothering to make targets of a framebuffer
        # interchangable
        self._framebuffer.blit(self._framebuffer2.value, wnd.width, wnd.height, GL_STENCIL_BUFFER_BIT, GL_NEAREST)
        self._framebuffer.blit(self._framebuffer3.value, wnd.width, wnd.height, GL_STENCIL_BUFFER_BIT, GL_NEAREST)
        
        # Apply SSCRV
        with self._framebuffer2.bind():        
            glStencilFunc(GL_EQUAL, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glStencilMask(0x00)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glUseProgram(self._sscrv_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.projection.I.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, self.camera.projection.flatten())
            glBindTextureUnit(0, self._framebuffer_depth.texture)
            glDrawArrays(GL_TRIANGLES, 0, 3)

        with self._framebuffer3.bind():        
            glStencilFunc(GL_EQUAL, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glStencilMask(0x00)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glUseProgram(self._adpt_kuwahara_program)
            glBindTextureUnit(0, self._framebuffer2_col.texture)
            glDrawArrays(GL_TRIANGLES, 0, 3)

        # Copy to back
        glClear(GL_COLOR_BUFFER_BIT)

        if self._option == 1:
            self._framebuffer3.blit_to_back(wnd.width, wnd.height, GL_COLOR_BUFFER_BIT, GL_NEAREST)
        else:
            self._framebuffer2.blit_to_back(wnd.width, wnd.height, GL_COLOR_BUFFER_BIT, GL_NEAREST)


    def _resize(self, wnd, width, height):
        self._framebuffer.resize(width, height)
        self._framebuffer2.resize(width, height)
        self._framebuffer3.resize(width, height)
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)


    def _keypress(self, wnd, key, x, y):
        # Move the camera
        shift = key.isupper()
        key = key.lower()
        move_amount = 0.1 + 0.9 * shift

        if key == b'w':
            self.camera.move_local(numpy.array([0, 0, move_amount]))
        elif key == b's':
            self.camera.move_local(numpy.array([0, 0, -move_amount]))

        elif key == b'a':
            self.camera.move_local(numpy.array([move_amount, 0, 0]))
        elif key == b'd':
            self.camera.move_local(numpy.array([-move_amount, 0, 0]))

        elif key == b'q':
            self.camera.move_local(numpy.array([0, move_amount, 0]))
        elif key == b'e':
            self.camera.move_local(numpy.array([0, -move_amount, 0]))

        elif key == b't':
            self._option ^= 1
            print("Option: {0}".format(self._option))

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
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height

        sin_u = sin(deriv_u * pi)
        cos_u = cos(deriv_u * pi)
        sin_v = sin(deriv_v * pi)
        cos_v = cos(deriv_v * pi)

        ortho = self.camera.orthonormal_basis
        
        # Y
        M = numpy.matrix([
            [cos_u, 0, sin_u],
            [0, 1, 0],
            [-sin_u, 0, cos_u],
        ])

        # XY stuff
        if button == wnd.RIGHT:
            N = numpy.matrix([
                [cos_v, -sin_v, 0],
                [sin_v, cos_v, 0],
                [0, 0, 1],
            ])
        else:
            N = numpy.matrix([
                [1, 0, 0],
                [0, cos_v, -sin_v],
                [0, sin_v, cos_v],
            ])
        N = ortho * N * ortho.I
        M *= N

        self.camera.append_3x3_transform(M)

        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()




