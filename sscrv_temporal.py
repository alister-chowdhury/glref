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

#line 62

layout(location = 0) uniform mat4 inverseProjection;
layout(location = 1) uniform mat4 projection;
layout(location = 2) uniform float previousPasses;

layout(binding = 0) uniform sampler2D depthPass;
layout(binding = 1) uniform sampler2D previousPass;

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outRgba;


// This should really be calculated based upon the scale of the scene.
// or configured manually.
#define RADIUS 0.1

#define SAMPLES_COUNT 8


#define GOLDEN_RATIO_2PI    10.16640738463051963161901802648439768366367858
#define GRAZING_ANGLE_DELTA 0.05

#define EASE_IN_JITTERING


// Generates vectors which more-or-less evenly sample the hemisphere of (0, 0, 1)
// exports vectors in batches of 4.
// Visualization: https://www.geogebra.org/3d/nfs8r7me
void make4HemisphereVector(float i,
                           float jitter,
                           out vec3 vecs[4])
{
    vec4 Z = vec4(i, i+1, i+2, i+3)/(SAMPLES_COUNT+1)
             + vec4(1/(SAMPLES_COUNT-1));

    // Visually a bit easier on the eyes
    #ifdef EASE_IN_JITTERING
         Z = fract(Z + jitter * 0.01 + GOLDEN_RATIO_2PI);

    // Converges faster by has a bit of a 'popping' like
    // quality as for all intents and purposes the jittering
    // is randomized.
    #else
         Z = fract(Z + jitter * GOLDEN_RATIO_2PI + GOLDEN_RATIO_2PI);

    #endif

        // For both ease-in and randomized jittering we are adding
        // GOLDEN_RATIO_2PI, for reasons I've yet to discover
        // it prevents this visible change in luminance where everything
        // seems to start of darker and then converge towards something
        // brighter.

         Z = (Z + GRAZING_ANGLE_DELTA) / (1 + GRAZING_ANGLE_DELTA);


    vec4 theta = (
                    vec4(i, i+1, i+2, i+3)
                    + jitter
                ) * GOLDEN_RATIO_2PI;

    vec4 R = sqrt(vec4(1) - Z*Z);
    vec4 X = cos(theta) * R;
    vec4 Y = sin(theta) * R;

    vecs[0] = vec3(X.x, Y.x, Z.x);
    vecs[1] = vec3(X.y, Y.y, Z.y);
    vecs[2] = vec3(X.z, Y.z, Z.z);
    vecs[3] = vec3(X.w, Y.w, Z.w);
}


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
        float theta = 6.28318530718 * fract(sin(dot(N.xy+previousPasses, vec2(12.9898,78.233))) * 43758.5453);
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

    vec3 hemisphereVecs[4];
    for (float i = 0; i < SAMPLES_COUNT; i+=4) {
        make4HemisphereVector(i,
                              previousPasses,
                              hemisphereVecs);
        for(uint j=0; j<4; ++j)
        {
            vec3 projNormal = TBN * hemisphereVecs[j];
            vec3 projPosition = position.xyz + projNormal * RADIUS;

            vec4 sampleUv      = projection * vec4(projPosition, 1.0);
                 sampleUv.xyz /= sampleUv.w;
                 sampleUv.xy   = sampleUv.xy * 0.5 + 0.5;

            sampleUv.xy = clamp(sampleUv.xy, vec2(0), vec2(1));

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
    }

    visibility /= SAMPLES_COUNT * 2;

    if(previousPasses > 0)
    {
        outRgba = mix(
            texture(previousPass, uv),
            vec4(visibility),
            (1 / (previousPasses+1))
        );
    }
    else
    {
        outRgba = vec4(visibility);
    }
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

        self.max_temporal_passes = 100
        self.dirty_base_update = True
        self.sscrv_swap_id = 0
        self.temporal_passes = 0

    def dirty_base(self):
        self.dirty_base_update = True
        self.temporal_passes = 0

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

        self._sscrv_col_swaps = [
            viewport.FramebufferTarget(GL_RGB32F, True),
            viewport.FramebufferTarget(GL_RGB32F, True),
        ]
        self._sscrv_stenil_swaps = [
            viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True),
            viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True),
        ]
        self._sscrv_fb_swaps = [
            viewport.Framebuffer(
                (self._sscrv_col_swaps[0], self._sscrv_stenil_swaps[0]),
                wnd.width,
                wnd.height
            ),
            viewport.Framebuffer(
                (self._sscrv_col_swaps[1], self._sscrv_stenil_swaps[1]),
                wnd.width,
                wnd.height
            ),
        ]

        # Second framebuffer so we can see things with renderdoc
        self._framebuffer2_col = viewport.FramebufferTarget(GL_RGB32F, True)
        self._framebuffer2_depth = viewport.FramebufferTarget(GL_DEPTH32F_STENCIL8, True)
        self._framebuffer2 = viewport.Framebuffer(
            (self._framebuffer2_col, self._framebuffer2_depth),
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
        if self.dirty_base_update:
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
            for swap in self._sscrv_fb_swaps:
                self._framebuffer.blit(swap.value, wnd.width, wnd.height, GL_STENCIL_BUFFER_BIT, GL_NEAREST)
            self.dirty_base_update = False

        # Apply SSCRV
        with self._sscrv_fb_swaps[self.sscrv_swap_id].bind():
            glStencilFunc(GL_EQUAL, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glStencilMask(0x00)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glUseProgram(self._sscrv_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.projection.I.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, self.camera.projection.flatten())
            glUniform1f(2, float(self.temporal_passes))
            glBindTextureUnit(0, self._framebuffer_depth.texture)
            glBindTextureUnit(1, self._sscrv_col_swaps[self.sscrv_swap_id^1].texture)
            glDrawArrays(GL_TRIANGLES, 0, 3)

        # Copy to back
        glClear(GL_COLOR_BUFFER_BIT)
        self._sscrv_fb_swaps[self.sscrv_swap_id].blit_to_back(
            wnd.width,
            wnd.height,
            GL_COLOR_BUFFER_BIT,
            GL_NEAREST
        )

        # Change swap id and refresh the window to begin another pass
        # if it's under what we allow for our budget
        self.sscrv_swap_id ^= 1
        self.temporal_passes += 1
        if self.temporal_passes < self.max_temporal_passes:
            wnd.redraw()


    def _resize(self, wnd, width, height):
        self._framebuffer.resize(width, height)
        self._sscrv_fb_swaps[0].resize(width, height)
        self._sscrv_fb_swaps[1].resize(width, height)
        self.dirty_base()
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

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # No redraw
        else:
            return

        self.dirty_base()
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
        self.dirty_base()
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()




