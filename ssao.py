from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport


DRAW_N_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;
layout(location = 2) in vec3 N;

layout(location = 0) out vec3 outP;
layout(location = 1) out vec3 outN;

void main() {
    vec4 worldP = model * vec4(P, 1.0);
    outP = worldP.xyz / worldP.w;
    vec4 worldN = inverse(transpose(model)) * vec4(N, 1.0);
    outN = normalize(worldN.xyz);
    gl_Position = modelViewProjection * vec4(P, 1.0);
}
"""

DRAW_N_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec3 P;
layout(location = 1) in vec3 N;
layout(location = 0) out vec3 outN;

void main() {
    outN = normalize(N);
    // Enable for geometric normals
    // outN = normalize(cross(dFdx(P), dFdy(P)));
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

SSAO_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 inverseProjection;
layout(location = 1) uniform mat4 viewInverseTranspose;
layout(location = 2) uniform mat4 projection;
layout(location = 3) uniform uint backface;  // When set to 1, reverse the normal
                                             // if it is facing away from the camera.
                                             //
                                             // This can cause artefacts at grazing angles
                                             // when not using face normals.
                                             // (Interpolated or mapped normals
                                             // may be facing away from the camera).

layout(binding = 0) uniform sampler2D normalPass; // This example uses world normals, but
                                                  // using view space normals would be a
                                                  // better idea.
                                                  // Especially as it would mean viewInverseTranspose
                                                  // doesn't need to be provided.

layout(binding = 1) uniform sampler2D depthPass;

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 outRgba;


// This should really be calculated based upon the scale of the scene.
// or configured manually.
#define RADIUS 0.1

// Samples to us
#ifndef SAMPLES_COUNT
#   define SAMPLES_COUNT 32
#endif


#define BIAS 0.001


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

    // Calculate the normal in view space,
    // Generate a orthonormal basis to orientate our hemisphere vectors
    // in the direction of the normal.
    mat3 TBN;
    {
        vec4 N = viewInverseTranspose * texture(normalPass, uv);
        N.xyz = normalize(N.xyz);

        // If we're doing back face stuff, make sure the normal is facing
        // the camera.
        if(backface == 1 && dot(position.xyz, N.xyz) > 0)
        {
            N = -N;
        }

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
        TBN = mat3(T, B, N.xyz);

        // Pre-rotate our matrix on the Z axis, by a random amount per-pixel.
        // This prevents visible banding that results from the the hemisphere vectors
        // probing the same directions on a surface with flat normals.
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
    // 4. If it is in-front mark that as an occlusion.

    float visibility = SAMPLES_COUNT;

    for (uint i = 0; i < SAMPLES_COUNT; ++i) {
        vec3 projNormal = TBN * HEMISPHERE_VECTORS[i];
        vec3 projPosition = position.xyz + projNormal * RADIUS;

        vec4 sampleUv      = projection * vec4(projPosition, 1.0);
             sampleUv.xyz /= sampleUv.w;
             sampleUv.xy   = sampleUv.xy * 0.5 + 0.5;

        float compareDepth = texture(depthPass, sampleUv.xy).x;
        if(!(compareDepth > 0 && compareDepth < 1)){ continue; }

        vec4 comparePosition = inverseProjection * vec4(2.0 * sampleUv.xy - 1.0, compareDepth, 1.0);
        comparePosition /= comparePosition.w;

        float occluded = float(projPosition.z + BIAS < comparePosition.z);

        // Attenuate the influence of the occlusion by the distance in viewspace depth
        // from the original position and sampled position.
        // (This seems to yield less haloing artefacts than distance or using projPosition).
        float attenuation = smoothstep(0,
                                       1,
                                       RADIUS / abs(position.z - comparePosition.z));

        visibility -= occluded * attenuation;
    }

    visibility /= SAMPLES_COUNT;
    outRgba = vec4(visibility);
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

        self._backface = 0

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
                viewport.ObjGeomAttr.UV,
                viewport.ObjGeomAttr.N
            )
        )

        self._main_geom_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1.5, 0, 1],
        ], dtype=numpy.float32)


        self._draw_n_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_N_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_N_FRAGMENT_SHADER_SOURCE
        )

        self._ssao_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=FULLSCREEN_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=SSAO_FRAGMENT_SHADER_SOURCE
        )

        self._framebuffer_n = viewport.FramebufferTarget(
            GL_RGB32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
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
            (self._framebuffer_n, self._framebuffer_depth),
            wnd.width,
            wnd.height
        )

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
        # Draw P, N + stencil-depth
        with self._framebuffer.bind():
            glStencilFunc(GL_ALWAYS, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
            glStencilMask(0xFF)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

            glUseProgram(self._draw_n_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, self._main_geom_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._main_geom_model * self.camera.view_projection).flatten())
            self.main_geom.draw()

        self._framebuffer.blit(self._framebuffer2.value, wnd.width, wnd.height, GL_STENCIL_BUFFER_BIT, GL_NEAREST)
        
        # Apply SSAO
        with self._framebuffer2.bind():        
            glStencilFunc(GL_EQUAL, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glStencilMask(0x00)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glUseProgram(self._ssao_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.projection.I.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, self.camera.view.I.T.flatten())
            glUniformMatrix4fv(2, 1, GL_FALSE, self.camera.projection.flatten())
            glUniform1ui(3, self._backface)
            glBindTextureUnit(0, self._framebuffer_n.texture)
            glBindTextureUnit(1, self._framebuffer_depth.texture)
            glDrawArrays(GL_TRIANGLES, 0, 3)

        # Copy to back
        glClear(GL_COLOR_BUFFER_BIT)
        self._framebuffer2.blit_to_back(wnd.width, wnd.height, GL_COLOR_BUFFER_BIT, GL_NEAREST)


    def _resize(self, wnd, width, height):
        self._framebuffer.resize(width, height)
        self._framebuffer2.resize(width, height)
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
            self._backface += 1
            if self._backface > 1:
                self._backface = 0
            print("Backface: {0}".format(self._backface))

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




