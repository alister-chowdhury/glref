import os
import struct
import time

import numpy
from OpenGL.GL import *

from viewport import make_permutation_program


_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders", "timer_samples256")
)


_RESET_TIMER_SAMPLES = make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER=os.path.join(_SHADER_DIR, "reset_timer_samples256.comp")
)

_APPEND_TIMER_SAMPLE = make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER=os.path.join(_SHADER_DIR, "append_timer_samples256.comp")
)

_DRAW_GRAPH = make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER=os.path.join(_SHADER_DIR, "draw_graph.vert"),
    GL_FRAGMENT_SHADER=os.path.join(_SHADER_DIR, "draw_graph.frag"),
)

_DRAW_GRAPH_LINES = make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER=os.path.join(_SHADER_DIR, "draw_graph_lines.vert"),
    GL_FRAGMENT_SHADER=os.path.join(_SHADER_DIR, "draw_graph_lines.frag"),
)

_DRAW_GRAPH_INFO = make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER=os.path.join(_SHADER_DIR, "draw_graph_info.vert"),
    GL_FRAGMENT_SHADER=os.path.join(_SHADER_DIR, "draw_graph_info.frag"),
)

_SIZEOF_TIMER_SAMPLES_256 = 4 * 4 + 256 * 4
_SIZEOF_DRAW_INPUT_256 = 3 * 4 * 4


class TimerSamples256Overlay(object):

    def __init__(self):
        self._timer256_ssbo = None
        self._draw256_ssbo = None
        self._dummy_vao = None
        self._enabled = True
        self._last_time = 0
        self._last_display_update = 0
        self._do_full_reset = False
        self._screen_display = None

        self._user_screen_display = (
            # x, y
            10, 10,
            # display ranges
            1000/144,
            1000/20,
            # warning / bad ranges
            1000/60, 1000/30,
            # width, height (pixels)
            256, 100,
            # font multiplier
            1.0
        )

    def toggle(self):
        self._enabled = not self._enabled
        self._last_time = 0
        self._last_display_update = 0

    def _update_ssbos(self, screen_width, screen_height):

        screen_display = self._user_screen_display + (screen_width, screen_height)
        update_draw_info = screen_display != self._screen_display

        if self._timer256_ssbo is None:
            update_draw_info = True
            self._do_full_reset = True
            ubo_ptrs = (ctypes.c_int * 2)()

            glCreateBuffers(2, ubo_ptrs)
            self._timer256_ssbo = ubo_ptrs[0]
            self._draw256_ssbo = ubo_ptrs[1]

            glNamedBufferStorage(
                self._timer256_ssbo,
                _SIZEOF_TIMER_SAMPLES_256,
                None,
                0
            )

            glNamedBufferStorage(
                self._draw256_ssbo,
                _SIZEOF_DRAW_INPUT_256,
                None,
                GL_DYNAMIC_STORAGE_BIT
            )

            vao_ptr = ctypes.c_int()
            glCreateVertexArrays(1, vao_ptr)
            self._dummy_vao = vao_ptr.value

        # Need to update stuff
        if update_draw_info:
            x = self._user_screen_display[0]
            y = self._user_screen_display[1]
            dispay_min = self._user_screen_display[2]
            dispay_max = self._user_screen_display[3]
            warning_value = self._user_screen_display[4]
            bad_value = self._user_screen_display[5]
            total_width = self._user_screen_display[6]
            total_height = self._user_screen_display[7]
            font_multiplier = self._user_screen_display[8]
            
            updated_info = numpy.zeros(12, dtype=numpy.float32)

            # vec4 valueRanges;
            updated_info[0] = dispay_min
            updated_info[1] = dispay_max
            updated_info[2] = warning_value
            updated_info[3] = bad_value

            # vec4 graphScreenBounds;
            updated_info[4] = x / screen_width
            updated_info[5] = x / screen_height
            updated_info[6] = (x + total_width) / screen_width
            updated_info[7] = (y + total_height) / screen_height

            # vec4 historyBounds;
            text_height = 8 * font_multiplier
            text_width = 6 * text_height
            text_screen_width = text_width / screen_width
            text_screen_height = text_height / screen_height
            updated_info[10] = (x + total_width - 4) / screen_width
            updated_info[11] = (y + total_height - 4) / screen_height
            updated_info[8] = updated_info[10] - text_screen_width
            updated_info[9] = updated_info[11] - text_screen_height

            data = updated_info.tobytes()

            glNamedBufferSubData(self._draw256_ssbo, 0, len(data), data)

    def update(self, screen_width, screen_height):

        if not self._enabled:
            return

        last_time = self._last_time
        now = time.time()
        self._last_time = now

        # Mkay, so this is the first time a capture
        # is being record, so we need to wait until
        # the next draw to record a sample.
        if last_time == 0:
            self._do_full_reset = True
            return

        delta_ms = 1000 * (now - last_time)

        # Ensure the SSBOs are allocated and that the draw inputs
        # match the screen and desired position
        self._update_ssbos(screen_width, screen_height)

        # Do a full reset if it's the first sample we've got
        # or append and optionally update the dispay text
        if self._do_full_reset:
            self._do_full_reset = False
            self._last_display_update = now
            glUseProgram(_RESET_TIMER_SAMPLES.one())
        else:
            updateDisplay = now - self._last_display_update > 0.05
            if updateDisplay:
                self._last_display_update = now
            glUseProgram(_APPEND_TIMER_SAMPLE.get(
                UPDATE_DISPLAY=int(updateDisplay)
            ))
        glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 0, self._timer256_ssbo, 0, _SIZEOF_TIMER_SAMPLES_256)
        glUniform1f(0, delta_ms)
        glDispatchCompute(1, 1, 1)

        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glBindVertexArray(self._dummy_vao)
        glUseProgram(_DRAW_GRAPH.one())
        glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 0, self._timer256_ssbo, 0, _SIZEOF_TIMER_SAMPLES_256)
        glBindBufferRange(GL_UNIFORM_BUFFER, 1, self._draw256_ssbo, 0, _SIZEOF_DRAW_INPUT_256)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glUseProgram(_DRAW_GRAPH_LINES.one())
        glDrawArrays(GL_LINES, 0, 4)

        glUseProgram(_DRAW_GRAPH_INFO.one())
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
