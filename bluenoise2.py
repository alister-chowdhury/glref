import os
from math import ceil, log
import random
from PIL import Image   # poor mans OIIO

import numpy

from OpenGL.GL import *

import viewport
import perf_overlay_lib


_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)


_VOID_AND_CLUSTER_UPDATE_ENERGY = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = os.path.join(_SHADER_DIR, "bluenoise2", "update_energy.comp")
)

_VOID_AND_CLUSTER_PICK = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = os.path.join(_SHADER_DIR, "bluenoise2", "pick.comp")
)

_BUFFER_TO_IMAGE = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = os.path.join(_SHADER_DIR, "draw_full_screen.vert"),
    GL_FRAGMENT_SHADER = os.path.join(_SHADER_DIR, "bluenoise2", "buffer_to_image.frag")
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

        self._use_storage_images = False

        self._tile_size = 8
        self._num_tiles = (32, 32)

        self._tile_size = 16
        self._num_tiles = (16, 16)

        self._tile_size = 32
        self._num_tiles = (8, 8)

        self._iteration = 0
        self._max_iterations_for_all_passes = self._tile_size * self._tile_size

        if (self._num_tiles[0] & 1) or (self._num_tiles[1] & 1):
            raise ValueError("Bad num tiles, must be aligned to 2")

        # We can quite comftably do an entire pass in a single frame
        self._max_iterations_per_frame = max(
            1,
            int(
                (8**2 / self._tile_size**2)
                * 256
                * (16 * 16) / (self._num_tiles[0] * self._num_tiles[1])
            )
        )


        self._dispatch_update_sizes = (
            (self._num_tiles[0] * self._tile_size) // 16,
            (self._num_tiles[1] * self._tile_size) // 16
        )
        self._dispatch_pick_sizes = (
            self._num_tiles[0] // 2,
            self._num_tiles[1] // 2
        )

        self._texture_size = (self._num_tiles[0] * self._tile_size, self._num_tiles[1] * self._tile_size)
        self._sigma = 1.9
        log2e = 1.4426950408889634073599246810018
        self._exp_multiplier = (self._sigma ** -2) * log2e

        print(
            (
                "TileSz    = {0}\n"
                "TextureSz = {1}x{2}\n"
                "MaxIters  = {3}"
            ).format(
                self._tile_size,
                self._texture_size[0], self._texture_size[1],
                self._max_iterations_per_frame
            )
        )

        self._reusable_tile_update_buffers = []

        self.timer_overlay = perf_overlay_lib.TimerSamples256Overlay()

        self._tile_preview = 0
        self._fft2_preview = 0
        self._cycle_noise = 0
        self._fft2_valid = False
        self._perf_overlay = False

        self._store_pixels_dir = None
        self._store_pixels_it = 0
        self._store_pixels_max = 1
        self._storing_pixels = False

    def run(self):
        self.window.run()

    def store_pixels(self):
        if self._store_pixels_it >= self._store_pixels_max:
            self._storing_pixels = False
            return

        def to_rgb_image(texture, dimensions):
            size = dimensions[0] * dimensions[1]
            pixel_data = bytearray(size)
            glGetTextureImage(
                texture,
                0,
                GL_RED,
                GL_UNSIGNED_BYTE,
                size,
                memoryview(pixel_data)
            )
            rgb_data = (
                numpy.frombuffer(pixel_data, dtype=numpy.uint8)
                .reshape(dimensions[1], dimensions[0])
            )
            return Image.fromarray(rgb_data)


        value_image_name = "bn_{0}_{1}x{2}_{3}_v.png".format(
            self._tile_size,
            self._texture_size[0],
            self._texture_size[1],
            self._store_pixels_it
        )
        
        dft_image_name = "bn_{0}_{1}x{2}_{3}_d.png".format(
            self._tile_size,
            self._texture_size[0],
            self._texture_size[1],
            self._store_pixels_it
        )

        value_image = os.path.join(self._store_pixels_dir, value_image_name)
        dft_image = os.path.join(self._store_pixels_dir, dft_image_name)


        to_rgb_image(self._value_texture, self._texture_size).save(
            value_image
        )

        to_rgb_image(self._fft2_p2_fb_target.texture, self._texture_size).save(
            dft_image
        )

        do_compression = False
        if do_compression:
            import subprocess
            subprocess.check_output(
                [
                    "curl",
                    "-X",
                    "POST",
                    "--form",
                    "input=@{0};type=image/png".format(value_image_name),
                    "https://www.toptal.com/developers/pngcrush/crush",
                    "--output",
                    value_image_name
                ],
                cwd=self._store_pixels_dir
            )

            subprocess.check_output(
                [
                    "curl",
                    "-X",
                    "POST",
                    "--form",
                    "input=@{0};type=image/png".format(dft_image),
                    "https://www.toptal.com/developers/pngcrush/crush",
                    "--output",
                    dft_image
                ],
                cwd=self._store_pixels_dir
            )

        self._store_pixels_it += 1


    def _init(self, wnd):

        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._void_and_cluster_pick_program = _VOID_AND_CLUSTER_PICK.get(
            TILE_SIZE=self._tile_size,
            USE_IMAGE_BUFFERS=int(self._use_storage_images)
        )
        self._void_and_cluster_update_energy_program = _VOID_AND_CLUSTER_UPDATE_ENERGY.get(
            TILE_SIZE=self._tile_size,
            USE_IMAGE_BUFFERS=int(self._use_storage_images)
        )

        if self._use_storage_images:
            self._energy_texture_ptr = ctypes.c_int()
            glCreateTextures(GL_TEXTURE_2D, 1, self._energy_texture_ptr)
            self._energy_texture = self._energy_texture_ptr.value
            glTextureParameteri(self._energy_texture, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTextureParameteri(self._energy_texture, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTextureParameteri(self._energy_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTextureParameteri(self._energy_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTextureStorage2D(
                self._energy_texture,
                1,
                GL_R32F,
                self._texture_size[0],
                self._texture_size[1]
            )

            self._value_texture_ptr = ctypes.c_int()
            glCreateTextures(GL_TEXTURE_2D, 1, self._value_texture_ptr)
            self._value_texture = self._value_texture_ptr.value
            glTextureParameteri(self._value_texture, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTextureParameteri(self._value_texture, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTextureParameteri(self._value_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTextureParameteri(self._value_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTextureStorage2D(
                self._value_texture,
                1,
                GL_R32F,
                self._texture_size[0],
                self._texture_size[1]
            )

            self._pick_texture_ptr = ctypes.c_int()
            glCreateTextures(GL_TEXTURE_2D, 1, self._pick_texture_ptr)
            self._pick_texture = self._pick_texture_ptr.value
            glTextureParameteri(self._pick_texture, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTextureParameteri(self._pick_texture, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTextureParameteri(self._pick_texture, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTextureParameteri(self._pick_texture, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTextureStorage2D(
                self._pick_texture,
                1,
                GL_RGBA32F,
                self._num_tiles[0],
                self._num_tiles[1]
            )
        
        else:
            
            self._buffer_to_image_program = _BUFFER_TO_IMAGE.get(
                TILE_SIZE=self._tile_size
            )

            self._tile_texture_buffer_size = (
                self._num_tiles[0] * self._num_tiles[1]
                 * 4 * 4
            )
            self._full_res_texture_buffer_size = (
                self._num_tiles[0] * self._tile_size
                * self._num_tiles[1] * self._tile_size
                * 4
            )

            storage_buffer_ptrs = (ctypes.c_int * 4)()
            glCreateBuffers(4, storage_buffer_ptrs)
            self._pick_buffer = storage_buffer_ptrs[0]
            self._energy_buffer = storage_buffer_ptrs[1]
            self._value_buffer = storage_buffer_ptrs[2]
            self._buffer_to_image_params = storage_buffer_ptrs[3]

            glNamedBufferStorage(
                self._pick_buffer,
                self._tile_texture_buffer_size,
                None,
                0
            )

            glNamedBufferStorage(
                self._energy_buffer,
                self._full_res_texture_buffer_size,
                None,
                0
            )

            glNamedBufferStorage(
                self._value_buffer,
                self._full_res_texture_buffer_size,
                None,
                0
            )

            buffer_to_image_params_data = numpy.array(
                [
                    self._num_tiles[0],
                    self._num_tiles[1],
                    0,
                    0,
                ],
                dtype=numpy.int32
            ).tobytes()

            glNamedBufferStorage(
                self._buffer_to_image_params,
                len(buffer_to_image_params_data),
                buffer_to_image_params_data,
                0
            )

            buffer_to_image_fb_target = viewport.FramebufferTarget(
                GL_R32F,
                True,
                custom_texture_settings={
                    GL_TEXTURE_WRAP_S: GL_REPEAT,
                    GL_TEXTURE_WRAP_T: GL_REPEAT,
                    GL_TEXTURE_MIN_FILTER: GL_NEAREST,
                    GL_TEXTURE_MAG_FILTER: GL_NEAREST,
                }
            )
            self._buffer_to_image_fb = viewport.Framebuffer(
                    (buffer_to_image_fb_target,),
                    self._texture_size[0],
                    self._texture_size[1]
                )
            self._value_texture = (
                buffer_to_image_fb_target.texture
            )


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

        if self._iteration == 0:

            clear_value = numpy.array([0, 0, 0, 0], dtype=numpy.float32)
            
            if self._use_storage_images:
                glClearTexImage(self._energy_texture, 0, GL_RGBA, GL_FLOAT, clear_value)
                glClearTexImage(self._value_texture, 0, GL_RGBA, GL_FLOAT, clear_value)
                glClearTexImage(self._pick_texture, 0, GL_RGBA, GL_FLOAT, clear_value)

            else:
                glClearNamedBufferSubData(
                    self._pick_buffer,
                    GL_RGBA32F,
                    0,
                    self._tile_texture_buffer_size,
                    GL_RGBA,
                    GL_FLOAT,
                    clear_value
                )
                glClearNamedBufferSubData(
                    self._energy_buffer,
                    GL_R32F,
                    0,
                    self._full_res_texture_buffer_size,
                    GL_RED,
                    GL_FLOAT,
                    clear_value
                )
                glClearNamedBufferSubData(
                    self._value_buffer,
                    GL_R32F,
                    0,
                    self._full_res_texture_buffer_size,
                    GL_RED,
                    GL_FLOAT,
                    clear_value
                )

        glMemoryBarrier(GL_UNIFORM_BARRIER_BIT)

        for iteration_index in range(self._max_iterations_per_frame):
            
            if self._iteration >= self._max_iterations_for_all_passes:
                break
            
            self._fft2_valid = False
            write_value = 1 - self._iteration / (self._max_iterations_for_all_passes - 1)
            self._iteration += 1

            if iteration_index >= len(self._reusable_tile_update_buffers):
                per_iteration_buffers_ptr = (ctypes.c_int * 4)()
                glCreateBuffers(4, per_iteration_buffers_ptr)
                for linear_tile_id in range(4):
                    glNamedBufferStorage(
                        per_iteration_buffers_ptr[linear_tile_id],
                        4 * 4 * 2,
                        None,
                        GL_DYNAMIC_STORAGE_BIT
                    )
                self._reusable_tile_update_buffers.append(
                    per_iteration_buffers_ptr
                )
            else:
                per_iteration_buffers_ptr = (
                    self._reusable_tile_update_buffers[iteration_index]
                )

            for linear_tile_id in range(4):
                if linear_tile_id == 0:
                    tile_offset_x = 0
                    tile_offset_y = 0
                elif linear_tile_id == 1:
                    tile_offset_x = 1
                    tile_offset_y = 1
                elif linear_tile_id == 2:
                    tile_offset_x = 1
                    tile_offset_y = 0
                else:
                    tile_offset_x = 0
                    tile_offset_y = 1

                tile_update_data = numpy.array(
                    [
                        numpy.int32(tile_offset_x).view(numpy.float32), # tileIdOffset.x
                        numpy.int32(tile_offset_y).view(numpy.float32), # tileIdOffset.y
                        numpy.int32(self._num_tiles[0]).view(numpy.float32), # numTiles.x
                        numpy.int32(self._num_tiles[1]).view(numpy.float32), # numTiles.y

                        self._exp_multiplier,                                           # expMultiplier
                        write_value,                                                    # writeValue
                        numpy.uint32(random.randint(0, 0x7fffff)).view(numpy.float32),  # randomSeed
                        # Padding
                        0,
                    ],
                    dtype=numpy.float32
                ).tobytes()

                target_buffer = per_iteration_buffers_ptr[linear_tile_id]
                glNamedBufferSubData(
                    target_buffer,
                    0,
                    len(tile_update_data),
                    tile_update_data
                )

                glUseProgram(self._void_and_cluster_update_energy_program)
                glBindBufferBase(GL_UNIFORM_BUFFER, 0, target_buffer)
                if self._use_storage_images:
                    glBindImageTexture(1, self._energy_texture, 0, 0, 0, GL_READ_WRITE, GL_R32F)
                    glBindImageTexture(2, self._pick_texture, 0, 0, 0, GL_READ_ONLY, GL_RGBA32F)
                else:
                    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._energy_buffer)
                    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._pick_buffer)
                glDispatchCompute(self._dispatch_update_sizes[0], self._dispatch_update_sizes[1], 1)

                glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

                glUseProgram(self._void_and_cluster_pick_program)
                glBindBufferBase(GL_UNIFORM_BUFFER, 0, target_buffer)
                if self._use_storage_images:
                    glBindImageTexture(1, self._energy_texture, 0, 0, 0, GL_READ_ONLY, GL_R32F)
                    glBindImageTexture(2, self._value_texture, 0, 0, 0, GL_READ_WRITE, GL_R32F)
                    glBindImageTexture(3, self._pick_texture, 0, 0, 0, GL_WRITE_ONLY, GL_RGBA32F)
                else:
                    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._energy_buffer)
                    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._value_buffer)
                    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._pick_buffer)
                glDispatchCompute(self._num_tiles[0]//2, self._num_tiles[1]//2, 1)
                
                glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)


        glBindVertexArray(viewport.get_dummy_vao())
        
        if not self._use_storage_images:
            glViewport(0, 0, self._texture_size[0], self._texture_size[1])
            with self._buffer_to_image_fb.bind():
                glUseProgram(self._buffer_to_image_program)
                glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._buffer_to_image_params)
                glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._value_buffer)
                glDrawArrays(GL_TRIANGLES, 0, 3)


        if (self._fft2_preview or self._storing_pixels) and not self._fft2_valid:
            self._fft2_valid = True
            glViewport(0, 0, self._texture_size[0], self._texture_size[1])
            with self._fft2_p1_fb.bind():
                glUseProgram(self._fft2_p1_program)
                glBindTextureUnit(0, self._value_texture)
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

        glBindTextureUnit(0, self._value_texture)
        glUniform2f(0, self._texture_size[0], self._texture_size[1])
        glDrawArrays(GL_TRIANGLES, 0, 3)

        if self._fft2_preview:
            glUseProgram(_VIS_BLUENOISE.get(VS_OUTPUT_UV=0))
            glBindTextureUnit(0, self._fft2_p2_fb_target.texture)
            glUniform2f(0, self._texture_size[0], self._texture_size[1])
            glDrawArrays(GL_TRIANGLES, 0, 3)

        if self._cycle_noise:
            if self._iteration >= self._max_iterations_for_all_passes:
                self._iteration = 0
                if self._storing_pixels:
                    self.store_pixels()

        if self._perf_overlay:
            self.timer_overlay.update(wnd.width, wnd.height)
            glDisable(GL_BLEND)
            glDisable(GL_DEPTH_TEST)
        wnd.redraw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        # Restart
        if key == b'r':
            self._iteration = 0
        elif key == b't':
            self._tile_preview ^= 1
        elif key == b'f':
            self._fft2_preview ^= 1
        elif key == b'c':
            self._cycle_noise ^= 1
        elif key == b'p':
            self._perf_overlay ^=1
        elif key == b's':
            if self._store_pixels_dir:
                self._storing_pixels ^= 1
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()
