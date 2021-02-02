from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport


VERTEX_SHADER_SOURCE = """
#version 450 core

layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 model_view_projection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;

layout(location = 0) out vec3 out_P;
layout(location = 1) out vec2 out_uv;

void main() {
    vec4 world_p = model * vec4(P, 1.0);
    out_P = world_p.xyz / world_p.w;
    out_uv = uv;
    gl_Position = model_view_projection * vec4(P, 1.0);
}
"""

FRAGMENT_SHADER_SOURCE = """
#version 450 core

layout(location = 2) uniform float mult = 1.0f;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;


layout(location = 0) out vec4 out_rgba;

void main() {
    out_rgba = vec4(mix(vec2(0.0), uv, mult), 0.0, 1.0);
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

        self.cube = None
        self.plane = None

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


        self._plane_reflection = viewport.make_reflection_matrix(
            viewport.PUV_PLANE_VERTICES[0:3],
            viewport.PUV_PLANE_VERTICES[5:8],
            viewport.PUV_PLANE_VERTICES[10:13],
        )

        self._draw_uvs_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=FRAGMENT_SHADER_SOURCE
        )


        self.camera.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self._draw_uvs_program)

        glUniformMatrix4fv(0, 1, GL_FALSE, self._cube_model.flatten())
        glUniformMatrix4fv(1, 1, GL_FALSE, (self._cube_model * self.camera.view_projection).flatten())
        glUniform1f(2, 1.0)
        self.cube.draw()

        # Record stencil
        glEnable(GL_STENCIL_TEST)
        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
        glStencilMask(0xFF)
        glClear(GL_STENCIL_BUFFER_BIT)
        glDepthMask(GL_FALSE)


        glUniformMatrix4fv(0, 1, GL_FALSE, self._plane_model.flatten())
        glUniformMatrix4fv(1, 1, GL_FALSE, (self._plane_model * self.camera.view_projection).flatten())
        glUniform1f(2, 0.25)

        self.plane.draw()

        # Stencil reflection
        glDepthMask(GL_TRUE)
        glStencilFunc(GL_EQUAL, 1, 0xFF)
        glStencilMask(0x00)

        reflection_model = self._cube_model * self._plane_reflection
        glUniformMatrix4fv(0, 1, GL_FALSE, reflection_model.flatten())
        glUniformMatrix4fv(1, 1, GL_FALSE, (reflection_model * self.camera.view_projection).flatten())
        glUniform1f(2, 0.125)
        self.cube.draw()

        glDisable(GL_STENCIL_TEST)


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)


    def _keypress(self, wnd, key, x, y):
        # Increase / Decrease Planes size
        if key == b'q':
            self._plane_model *= numpy.array([
                [1.1, 0, 0, 0],
                [0, 1.1, 0, 0],
                [0, 0, 1.1, 0],
                [0, 0, 0, 1],
            ])
        elif key == b'e':
            self._plane_model *= numpy.array([
                [1/1.1, 0, 0, 0],
                [0, 1/1.1, 0, 0],
                [0, 0, 1/1.1, 0],
                [0, 0, 0, 1],
            ])

         # Increase / Decrease Cube size
        elif key == b'z':
            self._cube_model *= numpy.array([
                [1.1, 0, 0, 0],
                [0, 1.1, 0, 0],
                [0, 0, 1.1, 0],
                [0, 0, 0, 1],
            ])
        elif key == b'x':
            self._cube_model *= numpy.array([
                [1/1.1, 0, 0, 0],
                [0, 1/1.1, 0, 0],
                [0, 0, 1/1.1, 0],
                [0, 0, 0, 1],
            ])

        # Move the camera
        elif key == b'w':
            self.camera.move(numpy.array([0, 1, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))
        elif key == b's':
            self.camera.move(numpy.array([0, -1, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))

        elif key == b'a':
            self.camera.move(numpy.array([1, 0, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))
        elif key == b'd':
            self.camera.move(numpy.array([-1, 0, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        elif key == b'n':
            self._cube_model[3,1] += 1
        elif key == b'm':
            self._cube_model[3,1] -= 1

        # No redraw
        else:
            return

        wnd.redraw()


    def _drag(self, wnd, x, y):
        # Move the cube around
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height

        sin_u = sin(deriv_u * pi)
        cos_u = cos(deriv_u * pi)
        sin_v = sin(deriv_v * pi)
        cos_v = cos(deriv_v * pi)

        translate_pivot = self._cube_model[3,:].flatten()
        self._cube_model[3,:] = [0, 0, 0, 1]

        self._cube_model *= numpy.array([
            [cos_u, 0, sin_u, 0],
            [0, 1, 0, 0],
            [-sin_u, 0, cos_u, 0],
            [0, 0, 0, 1],
        ])
        self._cube_model *= numpy.array([
            [1, 0, 0, 0],
            [0, cos_v, -sin_v, 0],
            [0, sin_v, cos_v, 0],
            [0, 0, 0, 1],
        ])

        self._cube_model[3,:] = translate_pivot
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()




