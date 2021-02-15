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

void main() {
    uv = vec2(
        float(gl_VertexID % 2),
        float(gl_VertexID / 2)
    );

    // TODO only draw within the boxs screen bounds
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);

}
"""

VOLUMEBOX_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(binding = 0) uniform sampler2D renderedCol;
layout(binding = 1) uniform sampler2D renderedDepth;

layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 out_rgba;

void main() {
    vec4 d = texture(renderedDepth, uv);
    float linearDistance = d.r/d.w;

    out_rgba = vec4(pow(linearDistance, 10.0));
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
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)



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

