from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport


DRAW_PREPASS_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec3 N;

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

OUTLINE_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;
layout(binding = 0) uniform usampler2D stencil;
layout(location = 0) out vec4 outRgba;


void main()
{
    uint s0 = texture(stencil, uv).x;
    if(s0 == 1)
    {
        outRgba = vec4(1.0);
    }
    else
    {
        outRgba = vec4(0.0);
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
        self.stencil_texture_view = None


    def run(self):
        self.window.run()

    def _init(self, wnd):
        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glDisable(GL_CULL_FACE)


        self.main_geom = viewport.load_obj(
            "data/armadillo.obj",
            (
                viewport.ObjGeomAttr.P,
                viewport.ObjGeomAttr.N
            )
        )

        self._main_geom_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1.5, 0, 1],
        ], dtype=numpy.float32)


        self._draw_prepass_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_PREPASS_VERTEX_SHADER_SOURCE
        )

        self._draw_outline_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=FULLSCREEN_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=OUTLINE_FRAGMENT_SHADER_SOURCE
        )

        self._pp_framebuffer_depth = viewport.FramebufferTarget(
            GL_DEPTH32F_STENCIL8,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )
        self._pp_framebuffer = viewport.Framebuffer(
            (self._pp_framebuffer_depth,),
            wnd.width,
            wnd.height
        )

        # Create a texture view for the stencil
        stencil_tv_ptr = ctypes.c_int()
        glGenTextures(1, stencil_tv_ptr) # glCreateTextures will not work
        self.stencil_texture_view = stencil_tv_ptr.value
        glTextureView(
            self.stencil_texture_view,
            GL_TEXTURE_2D,
            self._pp_framebuffer_depth.texture,
            self._pp_framebuffer_depth.pixel_type,
            0, 1,
            0, 1
        )
        glTextureParameteri(self.stencil_texture_view, GL_DEPTH_STENCIL_TEXTURE_MODE, GL_STENCIL_INDEX)

        self.camera.look_at(
            numpy.array([0, 3, 0]),
            numpy.array([0.83922848, 3.71858291, 0.52119542]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):
        with self._pp_framebuffer.bind():
            glStencilFunc(GL_ALWAYS, 1, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
            glStencilMask(0xFF)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            glUseProgram(self._draw_prepass_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, (self._main_geom_model * self.camera.view_projection).flatten())
            self.main_geom.draw()
        # self._framebuffer.blit(self._framebuffer2.value, wnd.width, wnd.height, GL_STENCIL_BUFFER_BIT, GL_NEAREST)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
        glUseProgram(self._draw_outline_program)
        glBindTextureUnit(0, self.stencil_texture_view)
        glDrawArrays(GL_TRIANGLES, 0, 3)


        # # Apply SSAO
        # with self._framebuffer2.bind():        
        #     glStencilFunc(GL_EQUAL, 1, 0xFF)
        #     glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
        #     glStencilMask(0x00)
        #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        #     glUseProgram(self._ssao_program)
        #     glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.projection.I.flatten())
        #     glUniformMatrix4fv(1, 1, GL_FALSE, self.camera.view.I.T.flatten())
        #     glUniformMatrix4fv(2, 1, GL_FALSE, self.camera.projection.flatten())
        #     glUniform1ui(3, self._backface)
        #     glBindTextureUnit(0, self._framebuffer_n.texture)
        #     glBindTextureUnit(1, self._framebuffer_depth.texture)
        #     glDrawArrays(GL_TRIANGLES, 0, 3)

        # # Copy to back
        # glClear(GL_COLOR_BUFFER_BIT)
        # self._framebuffer2.blit_to_back(wnd.width, wnd.height, GL_COLOR_BUFFER_BIT, GL_NEAREST)


    def _resize(self, wnd, width, height):
        self._pp_framebuffer.resize(width, height)
        
        # Regenerate texture view
        stencil_tv_ptr = ctypes.c_int()
        stencil_tv_ptr.value = self.stencil_texture_view
        glDeleteTextures(1, stencil_tv_ptr)

        glGenTextures(1, stencil_tv_ptr) # glCreateTextures will not work
        self.stencil_texture_view = stencil_tv_ptr.value
        glTextureView(
            self.stencil_texture_view,
            GL_TEXTURE_2D,
            self._pp_framebuffer_depth.texture,
            self._pp_framebuffer_depth.pixel_type,
            0, 1,
            0, 1
        )
        glTextureParameteri(self.stencil_texture_view, GL_DEPTH_STENCIL_TEXTURE_MODE, GL_STENCIL_INDEX)

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




