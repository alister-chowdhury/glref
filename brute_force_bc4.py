import os
from PIL import Image   # poor mans OIIO

import numpy

from OpenGL.GL import *
from OpenGL.GL.EXT import texture_compression_rgtc

import viewport

_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_BRUTE_FORCE_BC4_ITERATION = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = os.path.join(_SHADER_DIR, "brute_force_bc4_iteration.comp")
)

_BRUTE_FORCE_BC4_VIS = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "brute_force_bc4_quant_vis.frag")
)

_BRUTE_FORCE_BC4_PREV = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "brute_force_bc4_prev.frag")
)

_BRUTE_FORCE_BC4_FINALIZE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = os.path.join(_SHADER_DIR, "brute_force_bc4_finalize.comp")
)


class Renderer(object):

    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self._iteration = 0
        self._show_quant = 1
        self._show_bc4_texture = 0
        self._write_bc4_out_texture = 0
        self._made_bc4_texture = False
        self._current_bc4_bytes = None

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)

        self._brute_force_bc4_iter_program = _BRUTE_FORCE_BC4_ITERATION.get()
        self._brute_force_bc4_finalize_program = _BRUTE_FORCE_BC4_FINALIZE.get()

        bluenoise = Image.open("data/bn/BlueNoise64Tiled.png")
        bluenoise_data = numpy.array(bluenoise.getdata(), dtype=numpy.uint8)

        self._bn_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._bn_texture_ptr)
        self._bluenoise_tex = self._bn_texture_ptr.value

        glTextureParameteri(self._bluenoise_tex, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._bluenoise_tex, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTextureParameteri(self._bluenoise_tex, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTextureParameteri(self._bluenoise_tex, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTextureStorage2D(
            self._bluenoise_tex,
            1,
            GL_R8,
            bluenoise.width,
            bluenoise.height
        )
        glTextureSubImage2D(
            self._bluenoise_tex, 0, 0, 0,
            bluenoise.width, bluenoise.height,
            GL_RGBA, GL_UNSIGNED_BYTE,
            bluenoise_data
        )

        self._bc4_iter_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._bc4_iter_texture_ptr)
        self._bc4_iter_tex = self._bc4_iter_texture_ptr.value

        glTextureParameteri(self._bc4_iter_tex, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._bc4_iter_tex, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTextureParameteri(self._bc4_iter_tex, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTextureParameteri(self._bc4_iter_tex, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTextureStorage2D(
            self._bc4_iter_tex,
            1,
            GL_RGBA32F,
            bluenoise.width >> 2,
            bluenoise.height >> 2
        )

        self._bc4_final_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._bc4_final_texture_ptr)
        self._bc4_final_tex = self._bc4_final_texture_ptr.value

        glTextureParameteri(self._bc4_final_tex, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._bc4_final_tex, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTextureParameteri(self._bc4_final_tex, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTextureParameteri(self._bc4_final_tex, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTextureStorage2D(
            self._bc4_final_tex,
            1,
            GL_RG32UI,
            bluenoise.width >> 2,
            bluenoise.height >> 2
        )

        self._bc4_preview_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._bc4_preview_texture_ptr)
        self._bc4_preview_tex = self._bc4_preview_texture_ptr.value

        glTextureParameteri(self._bc4_preview_tex, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._bc4_preview_tex, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTextureParameteri(self._bc4_preview_tex, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTextureParameteri(self._bc4_preview_tex, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTextureStorage2D(
            self._bc4_preview_tex,
            1,
            texture_compression_rgtc.GL_COMPRESSED_RED_RGTC1_EXT,
            bluenoise.width,
            bluenoise.height
        )

        self._bc4_texture_size = (bluenoise.width >> 2, bluenoise.height >> 2)
        self._texture_size = (bluenoise.width, bluenoise.height)
        self._inv_texture_size = (1.0 / bluenoise.width, 1.0 / bluenoise.height)

        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):
        if self._iteration == 0:
            clear_value = numpy.array([0, 0, float("inf"), 0], dtype=numpy.float32)
            glClearTexImage(self._bc4_iter_tex, 0, GL_RGBA, GL_FLOAT, clear_value)
            self._iteration += 1

        if self._iteration < 256:
            glUseProgram(self._brute_force_bc4_iter_program)
            glUniform2i(1, self._bc4_texture_size[0], self._bc4_texture_size[1])
            glUniform2f(2, self._inv_texture_size[0], self._inv_texture_size[1])

            glBindTextureUnit(0, self._bluenoise_tex)
            glBindImageTexture(
                1,
                self._bc4_iter_tex,
                0,
                0,
                0,
                GL_READ_WRITE,
                GL_RGBA32F
            )
            
            glUniform1i(0, self._iteration)
            glDispatchCompute(
                (self._bc4_texture_size[0] + 7)//8,
                (self._bc4_texture_size[1] + 7)//8,
                1
            )
            # lazy
            glMemoryBarrier(GL_ALL_BARRIER_BITS)
            self._iteration += 1
            self._made_bc4_texture = False

        need_bc4_texture = self._show_bc4_texture | self._write_bc4_out_texture

        if need_bc4_texture and (self._made_bc4_texture is False):
            self._made_bc4_texture = True
            glUseProgram(self._brute_force_bc4_finalize_program)
            glUniform2i(0, self._bc4_texture_size[0], self._bc4_texture_size[1])
            glUniform2f(1, self._inv_texture_size[0], self._inv_texture_size[1])
            glBindTextureUnit(0, self._bluenoise_tex)
            glBindImageTexture(
                1,
                self._bc4_iter_tex,
                0,
                0,
                0,
                GL_READ_ONLY,
                GL_RGBA32F
            )
            glBindImageTexture(
                2,
                self._bc4_final_tex,
                0,
                0,
                0,
                GL_WRITE_ONLY,
                GL_RG32UI
            )
            glDispatchCompute(
                (self._bc4_texture_size[0] + 7)//8,
                (self._bc4_texture_size[1] + 7)//8,
                1
            )
            # lazy
            glMemoryBarrier(GL_ALL_BARRIER_BITS)

            size = self._bc4_texture_size[0] * self._bc4_texture_size[1] * 4 * 2
            self._current_bc4_bytes = bytearray(size)
            glGetTextureImage(
                self._bc4_final_tex,
                0,
                GL_RG_INTEGER,
                GL_UNSIGNED_INT,
                size,
                memoryview(self._current_bc4_bytes)
            )
            glCompressedTextureSubImage2D(
                self._bc4_preview_tex,
                0,
                0, 0,
                self._texture_size[0], self._texture_size[1],
                texture_compression_rgtc.GL_COMPRESSED_RED_RGTC1_EXT,
                size,
                memoryview(self._current_bc4_bytes)
            )

        if self._write_bc4_out_texture:
            self._write_bc4_out_texture = 0
            with open("data/bn/BlueNoise64Tiled.bc4", "wb") as out_fp:
                out_fp.write(self._current_bc4_bytes)


        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_FALSE)
        glDepthMask(GL_FALSE)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_ONE, GL_ONE)

        if self._show_bc4_texture:
            glUseProgram(_BRUTE_FORCE_BC4_PREV.get(
                VS_OUTPUT_UV=0
            ))
            glBindTextureUnit(0, self._bc4_preview_tex)
        else:
            glUseProgram(_BRUTE_FORCE_BC4_VIS.get(
                VS_OUTPUT_UV=0,
                SHOW_BC_QUANTIZATION=self._show_quant
            ))
            glBindTextureUnit(0, self._bluenoise_tex)
            glBindTextureUnit(1, self._bc4_iter_tex)

        glUniform2f(0, self._texture_size[0], self._texture_size[1])
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_TRIANGLES, 0, 3)

        glBlendFunc(GL_ONE, GL_ZERO)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_TRUE)
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        # Restart
        if key == b'r':
            self._iteration = 0
        if key == b'q':
            self._show_quant ^= 1
        if key == b'b':
            self._show_bc4_texture ^= 1
        if key == b'w':
            self._write_bc4_out_texture = 1
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()
