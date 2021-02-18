from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport


SCENE_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;

layout(location = 0) out vec3 out_P;
layout(location = 1) out vec2 out_uv;

void main() {
    vec4 world_p = model * vec4(P, 1.0);
    out_P = world_p.xyz / world_p.w;
    out_uv = uv;
    gl_Position = modelViewProjection * vec4(P, 1.0);
}
"""

SCENE_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 2) uniform float mult = 1.0f;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;


layout(location = 0) out vec4 out_rgba;

void main() {
    out_rgba = vec4(mix(vec2(0.0), uv, mult), 0.0, 1.0);
}
"""

VOLUMEBOX_VERTEX_SHADER_SOURCE = """
#version 460 core
layout(location = 0) out vec2 uv;


layout(location = 0) uniform vec3 P0;
layout(location = 1) uniform vec3 P1;
layout(location = 2) uniform mat4 viewPerspective;
layout(location = 3) uniform mat4 inversePerspective;
layout(location = 4) uniform mat4 inverseView;
layout(location = 5) uniform vec3 eye;



vec4 getScreenBbox(vec4 bboxA, vec4 bboxB)
{
    mat4 bboxBlockA = viewPerspective * mat4(
        bboxA,
        vec4(bboxA.x, bboxB.yzw),
        vec4(bboxA.xy, bboxB.zw),
        vec4(bboxA.x, bboxB.y, bboxA.zw)
    );
    bboxBlockA[0] /= bboxBlockA[0].w;
    bboxBlockA[1] /= bboxBlockA[1].w;
    bboxBlockA[2] /= bboxBlockA[2].w;
    bboxBlockA[3] /= bboxBlockA[3].w;

    mat4 bboxBlockB = viewPerspective * mat4(
        bboxB,
        vec4(bboxB.x, bboxA.yzw),
        vec4(bboxB.xy, bboxA.zw),
        vec4(bboxB.x, bboxA.y, bboxB.zw)
    );
    bboxBlockB[0] /= bboxBlockB[0].w;
    bboxBlockB[1] /= bboxBlockB[1].w;
    bboxBlockB[2] /= bboxBlockB[2].w;
    bboxBlockB[3] /= bboxBlockB[3].w;

    vec2 xy_mins = min(
        min(min(bboxBlockA[0].xy, bboxBlockA[1].xy), min(bboxBlockA[2].xy, bboxBlockA[3].xy)),
        min(min(bboxBlockB[0].xy, bboxBlockB[1].xy), min(bboxBlockB[2].xy, bboxBlockB[3].xy))
    );
    vec2 xy_maxs = max(
        max(max(bboxBlockA[0].xy, bboxBlockA[1].xy), max(bboxBlockA[2].xy, bboxBlockA[3].xy)),
        max(max(bboxBlockB[0].xy, bboxBlockB[1].xy), max(bboxBlockB[2].xy, bboxBlockB[3].xy))
    );

    return vec4(xy_mins, xy_maxs);
}


void main() {
    uv = vec2(
        float(gl_VertexID % 2),
        float(gl_VertexID / 2)
    );

    vec4 screenBbox = getScreenBbox(
        vec4(P0, 1.0),
        vec4(P1, 1.0)
    );

    uv = max(uv, (screenBbox.xy + 1.0) * 0.5);
    uv = min(uv, (screenBbox.zw + 1.0) * 0.5);

    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);

}
"""

VOLUMEBOX_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(binding = 0) uniform sampler2D renderedCol;
layout(binding = 1) uniform sampler2D renderedDepth;


layout(location = 0) uniform vec3 P0;
layout(location = 1) uniform vec3 P1;
layout(location = 2) uniform mat4 viewPerspective;
layout(location = 3) uniform mat4 inversePerspective;
layout(location = 4) uniform mat4 inverseView;
layout(location = 5) uniform vec3 eye;

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 out_rgba;

vec3 getWorldPos(float depth) {
    vec4 clipSpaceP = vec4(
        uv * 2.0 - 1.0,
        depth * 2.0 - 1.0,
        1.0
    );
    vec4 viewSpaceP = inversePerspective * clipSpaceP;
    viewSpaceP /= viewSpaceP.w;
    return (inverseView * viewSpaceP).xyz;
}

void main() {
    float depth = texture(renderedDepth, uv).x;
    vec3 screenP = getWorldPos(depth);

    vec3 direction = normalize(screenP - eye);
    
    vec3 t0 = (P0 - eye) / direction;
    vec3 t1 = (P1 - eye) / direction;

    vec3 tmin = min(t0, t1);
    vec3 tmax = max(t0, t1);

    float tnear = max(max(tmin.x, tmin.y), tmin.z);
    float tfar = min(min(min(tmax.x, tmax.y), tmax.z), distance(eye, screenP));


    if(tnear > tfar || tfar < 0)
    {
        discard;
    }

    vec3 intersectionStart = eye + direction * (tnear * float(tnear > 0.0));
    vec3 intersectionEnd = eye + direction * tfar;

    vec3 textureUvwStart = (intersectionStart - P0) / (P1 - P0);
    vec3 textureUvwEnd = (intersectionEnd - P0) / (P1 - P0);

    float density = distance(textureUvwEnd, textureUvwStart);
    out_rgba = texture(renderedCol, uv) * (1.0-density);

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


    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self.cube = viewport.StaticGeometry(
            (3, 2), # P, UV
            viewport.CUBE_INDICES,
            viewport.PUV_CUBE_VERTICES,
        )
        self.plane = viewport.StaticGeometry(
            (3, 2),
            viewport.PLANE_INDICES,
            viewport.PUV_PLANE_VERTICES,
        )

        self._cube_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1.5, 0, 1],
        ], dtype=numpy.float32)

        self._plane_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0.5],
        ], dtype=numpy.float32)

        self._draw_scene_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=SCENE_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=SCENE_FRAGMENT_SHADER_SOURCE
        )
        self._draw_volume_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=VOLUMEBOX_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=VOLUMEBOX_FRAGMENT_SHADER_SOURCE
        )

        self._framebuffer_col = viewport.FramebufferTarget(GL_RGBA8, True)
        self._framebuffer_depth = viewport.FramebufferTarget(GL_DEPTH_COMPONENT, True)
        self._framebuffer = viewport.Framebuffer(
            (self._framebuffer_col, self._framebuffer_depth),
            wnd.width,
            wnd.height
        )

        self.camera.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):

        # Draw the scene to the framebuffer
        with self._framebuffer.bind():
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glUseProgram(self._draw_scene_program)

            glUniformMatrix4fv(0, 1, GL_FALSE, self._cube_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._cube_model * self.camera.view_projection).flatten())
            glUniform1f(2, 1.0)
            self.cube.draw()

            glUniformMatrix4fv(0, 1, GL_FALSE, self._plane_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._plane_model * self.camera.view_projection).flatten())
            glUniform1f(2, 0.25)

            self.plane.draw()

        # Copy the framebuffer to the back
        self._framebuffer.blit_to_back(
            wnd.width,
            wnd.height,
            GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT,
            GL_NEAREST
        )

        glUseProgram(self._draw_volume_program)
        glBindTextureUnit(0, self._framebuffer_col.texture)
        glBindTextureUnit(1, self._framebuffer_depth.texture)
        glUniform3f(0, -2, -2, -2)
        glUniform3f(1, 2, 2, 2)
        glUniformMatrix4fv(2, 1, GL_FALSE, self.camera.view_projection.flatten())
        glUniformMatrix4fv(3, 1, GL_FALSE, self.camera.projection.I.flatten())
        glUniformMatrix4fv(4, 1, GL_FALSE, self.camera.view.I.flatten())
        glUniform3f(5, self.camera.eye[0], self.camera.eye[1], self.camera.eye[2])
        
        glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glDepthMask(GL_TRUE)
        glEnable(GL_DEPTH_TEST)

    def _resize(self, wnd, width, height):
        self._framebuffer.resize(width, height)
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)

    def _keypress(self, wnd, key, x, y):
        # Move the camera
        if key == b'w':
            self.camera.move_local(numpy.array([0, 0, 1]))
        elif key == b's':
            self.camera.move_local(numpy.array([0, 0, -1]))

        elif key == b'a':
            self.camera.move_local(numpy.array([1, 0, 0]))
        elif key == b'd':
            self.camera.move_local(numpy.array([-1, 0, 0]))

        elif key == b'q':
            self.camera.move_local(numpy.array([0, 1, 0]))
        elif key == b'e':
            self.camera.move_local(numpy.array([0, -1, 0]))

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

