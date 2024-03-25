import os
from math import ceil, log
import random
from PIL import Image   # poor mans OIIO

import numpy

from OpenGL.GL import *

import viewport

_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)


_VOID_AND_CLUSTER_INIT = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "void_and_cluster_init.frag")
)

_VOID_AND_CLUSTER_REDUCE_INIT = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "void_and_cluster_reduce_init.frag")
)

_VOID_AND_CLUSTER_REDUCE_ITER = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "void_and_cluster_reduce_iter.frag")
)

_VOID_AND_CLUSTER_UPDATE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "void_and_cluster_update.frag")
)

_VOID_AND_CLUSTER_PARTIAL_UPDATE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "void_and_cluster_partial_update.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "void_and_cluster_update.frag")
)

_VIS_BLUENOISE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise", "vis_bluenoise.frag")
)


_GEN_FFT2_P1 = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "dft", "fft2_p1.frag")
)

_GEN_FFT2_P2 = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "dft", "fft2_p2.frag")
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
        self._max_iterations_per_frame = 64
        self._texture_size = (64, 64)
        self._background_seed = random.randint(0, 0x7fffff)
        self._inv_texture_size = (1.0 / self._texture_size[0], 1.0 / self._texture_size[1])
        self._inv_num_pixels = 1.0 / (self._texture_size[0] * self._texture_size[1] - 1)
        self._sigma = 1.9
        log2e = 1.4426950408889634073599246810018
        self._exp_multiplier = (self._sigma ** -2) * log2e

        # Figure out the update span range, and if we just need to fallback
        # on updating the full screen
        self._target_accuracy = 0.99

        if self._target_accuracy >= 1.0 or self._target_accuracy <= 0.0:
            self._update_span = max(self._texture_size[0], self._texture_size[1])
        else:
            self._update_span = int(ceil(-log(1 - self._target_accuracy) * self._sigma ** 2))

        # Only do partial updates if there are no overlaps
        self._partial_update_bias = 0.01
        self._do_partial_update = (
            (self._update_span * 2 + self._partial_update_bias)
            < min(self._texture_size[0], self._texture_size[1])
        )


        self._tile_preview = 0
        self._fft2_preview = 0
        self._fft2_valid = False

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._void_and_cluster_init_program = _VOID_AND_CLUSTER_INIT.get()
        self._void_and_cluster_reduce_init_program = _VOID_AND_CLUSTER_REDUCE_INIT.get()
        self._void_and_cluster_reduce_iter_program = _VOID_AND_CLUSTER_REDUCE_ITER.get()
        self._void_and_cluster_update_partial_program = _VOID_AND_CLUSTER_PARTIAL_UPDATE.get()
        self._void_and_cluster_update_program = _VOID_AND_CLUSTER_UPDATE.get()

        self._noise_energy_fb_target = viewport.FramebufferTarget(
            GL_RG32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_REPEAT,
                GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                GL_TEXTURE_MAG_FILTER: GL_NEAREST,
            }
        )

        self._noise_energy_fb = viewport.Framebuffer(
            (self._noise_energy_fb_target,),
            self._texture_size[0],
            self._texture_size[1]
        )

        # Build void and cluster reduction buffers
        void_and_cluster_dims = (
            (self._texture_size[0] + 7) // 8,
            (self._texture_size[1] + 7) // 8
        )
        self._void_and_cluster_data = []

        while True:
            target = viewport.FramebufferTarget(
                GL_RG32F,
                True,
                custom_texture_settings={
                    GL_TEXTURE_WRAP_S: GL_REPEAT,
                    GL_TEXTURE_WRAP_T: GL_REPEAT,
                    GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                    GL_TEXTURE_MAG_FILTER: GL_NEAREST,
                }
            )
            framebuffer = viewport.Framebuffer(
                (target,),
                void_and_cluster_dims[0],
                void_and_cluster_dims[1]
            )
            self._void_and_cluster_data.append((
                target,
                framebuffer,
                void_and_cluster_dims
            ))

            if (void_and_cluster_dims[0] == 1
                    and void_and_cluster_dims[1] == 1):
                break

            new_x = (void_and_cluster_dims[0] + 7) // 8
            new_y = (void_and_cluster_dims[1] + 7) // 8
            if new_x == 0:
                new_x = 1
            if new_y == 0:
                new_y = 1
            void_and_cluster_dims = (new_x, new_y)

        self._fft2_p1_program = _GEN_FFT2_P1.get(EXTRACT_RED=1)
        self._fft2_p2_program = _GEN_FFT2_P2.get(OUTPUT_LENGTH=1)

        self._fft2_p1_fb_target = viewport.FramebufferTarget(
            GL_RG32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_REPEAT,
                GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                GL_TEXTURE_MAG_FILTER: GL_NEAREST,
            }
        )
        self._fft2_p1_fb = viewport.Framebuffer(
                (self._fft2_p1_fb_target,),
                self._texture_size[0],
                self._texture_size[1]
            )

        self._fft2_p2_fb_target = viewport.FramebufferTarget(
            GL_R32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_REPEAT,
                GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                GL_TEXTURE_MAG_FILTER: GL_NEAREST,
            }
        )
        self._fft2_p2_fb = viewport.Framebuffer(
                (self._fft2_p2_fb_target,),
                self._texture_size[0],
                self._texture_size[1]
            )

        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):

        glViewport(0, 0, self._texture_size[0], self._texture_size[1])

        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_ONE, GL_ZERO)

        if self._iteration == 0:
            glDisable(GL_BLEND)
            with self._noise_energy_fb.bind():
                glUseProgram(self._void_and_cluster_init_program)
                background_seed = random.randint(0, 0x7fffff)
                glUniform1ui(0, background_seed)
                glBindVertexArray(viewport.get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 3)


        for _ in range(self._max_iterations_per_frame):
            glDisable(GL_BLEND)
            if self._iteration < (self._texture_size[0] * self._texture_size[1] - 1):
                # Reduce down to find void and clusters
                collapsed_void_data = self._noise_energy_fb_target.texture
                max_void_cluster_dim = self._texture_size

                for i, data in enumerate(self._void_and_cluster_data):
                    target, framebuffer, dim = data
                    glViewport(0, 0, dim[0], dim[1])
                    with framebuffer.bind():
                        if i == 0:
                            glUseProgram(self._void_and_cluster_reduce_init_program)
                        else:
                            glUseProgram(self._void_and_cluster_reduce_iter_program)
                        glBindTextureUnit(0, collapsed_void_data)
                        seed = random.randint(0, 0x7fffff)
                        glUniform3ui(0, max_void_cluster_dim[0], max_void_cluster_dim[1], seed)
                        glBindVertexArray(viewport.get_dummy_vao())
                        glDrawArrays(GL_TRIANGLES, 0, 3)
                    
                    max_void_cluster_dim = dim
                    collapsed_void_data = target.texture

                # Update noise and energy
                glEnable(GL_BLEND)
                glBlendFunc(GL_ONE, GL_ONE)
                glViewport(0, 0, self._texture_size[0], self._texture_size[1])
                with self._noise_energy_fb.bind():
                    if self._do_partial_update:
                        glUseProgram(self._void_and_cluster_update_partial_program)
                        glUniform1i(3, self._update_span)
                    else:
                        glUseProgram(self._void_and_cluster_update_program)
                    glBindTextureUnit(0, collapsed_void_data)
                    glUniform4f(
                        0,
                        self._texture_size[0],
                        self._texture_size[1],
                        self._inv_texture_size[0], 
                        self._inv_texture_size[1]
                    )
                    glUniform1f(1, self._exp_multiplier)
                    glUniform1f(2, 1.0 - (self._iteration * self._inv_num_pixels))
                    glBindVertexArray(viewport.get_dummy_vao())

                    if self._do_partial_update:
                        glDrawArrays(GL_TRIANGLES, 0, 3 * 8)
                    else:
                        glDrawArrays(GL_TRIANGLES, 0, 3)
                    self._iteration += 1

                self._fft2_valid = False

                glBlendFunc(GL_ONE, GL_ZERO)
            else:
                break


        if self._fft2_preview and not self._fft2_valid:
            self._fft2_valid = True
            glViewport(0, 0, self._texture_size[0], self._texture_size[1])
            with self._fft2_p1_fb.bind():
                glUseProgram(self._fft2_p1_program)
                glBindTextureUnit(0, self._noise_energy_fb_target.texture)
                glDrawArrays(GL_TRIANGLES, 0, 3)
            with self._fft2_p2_fb.bind():
                glUseProgram(self._fft2_p2_program)
                glBindTextureUnit(0, self._fft2_p1_fb_target.texture)
                glDrawArrays(GL_TRIANGLES, 0, 3)

        # Draw preview
        glViewport(0, 0, wnd.width, wnd.height)
        glClear(GL_COLOR_BUFFER_BIT)

        if self._tile_preview:
            glUseProgram(_VIS_BLUENOISE.get(TILE_SAMPLE=1))
        else:
            glUseProgram(_VIS_BLUENOISE.get(VS_OUTPUT_UV=0))

        glBindTextureUnit(0, self._noise_energy_fb_target.texture)

        glUniform2f(0, self._texture_size[0], self._texture_size[1])
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_TRIANGLES, 0, 3)


        if self._fft2_preview:
            glUseProgram(_VIS_BLUENOISE.get(VS_OUTPUT_UV=0))
            glBindTextureUnit(0, self._fft2_p2_fb_target.texture)
            glUniform2f(0, self._texture_size[0], self._texture_size[1])
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

        wnd.redraw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        # Restart
        if key == b'r':
            self._iteration = 0
        if key == b't':
            self._tile_preview ^= 1
        if key == b'f':
            self._fft2_preview ^= 1
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()
