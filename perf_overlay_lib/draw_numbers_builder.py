import os
import struct

import numpy
from OpenGL.GL import *


from viewport import load_shader_source, generate_shader_program


_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DRAW_MULTI_NUMBERS_VERT_PATH = os.path.join(
    _SHADER_DIR, "draw_multi_numbers.vert"
)

_DRAW_NUMBER_FRAG_PATH = os.path.join(
    _SHADER_DIR, "draw_number.frag"
)

_DRAW_MULTI_NUMBERS_PROGRAMS = {}


def _get_draw_multi_numbers_program():
    key = ()
    if key not in _DRAW_MULTI_NUMBERS_PROGRAMS:
        _DRAW_MULTI_NUMBERS_PROGRAMS[key] = generate_shader_program(
            GL_VERTEX_SHADER=load_shader_source(_DRAW_MULTI_NUMBERS_VERT_PATH),
            GL_FRAGMENT_SHADER=load_shader_source(
                _DRAW_NUMBER_FRAG_PATH,
            )
        )
    return _DRAW_MULTI_NUMBERS_PROGRAMS[key]


class DrawNumbersBuilder(object):

    def __init__(self):
        self._ubo = None
        self._ubo_capacity = 0
        self._dummy_vao = None
        self._queue = []

    def __del__(self):
        if self._ubo is not None:
            ubo_ptr = self._ubo
            glDeleteBuffers(1, ubo_ptr)
        if self._dummy_vao is not None:
            vao_ptr = ctypes.c_int()
            vao_ptr.value = self._dummy_vao
            glDeleteVertexArrays(1, vao_ptr)

    def add(self, number, bounds, bg_col, fg_col):

        bounds = struct.pack("ffff", *bounds)

        if isinstance(number, float):
            number = struct.pack("f", number)
            number_type = b'\x02\x00\x00\x00'
        elif number >= 0:
            number = struct.pack("I", number)
            number_type = b'\x01\x00\x00\x00'
        else:
            number = struct.pack("i", number)
            number_type = b'\x00\x00\x00\x00'

        assert(len(bg_col) == 4)
        assert(len(fg_col) == 4)

        bg_col = (
            numpy.array(bg_col, dtype=numpy.float32)
            * 255
        ).astype(numpy.uint8).tobytes()

        fg_col = (
            numpy.array(fg_col, dtype=numpy.float32)
            * 255
        ).astype(numpy.uint8).tobytes()

        new_entry = bounds + number + number_type + bg_col + fg_col

        self._queue.append(new_entry)

    def flush(self):
        if self._queue:
            data = b"".join(self._queue)
            count = len(self._queue)
            self._queue = []

            data_size = len(data)

            if self._dummy_vao is None:
                vao_ptr = ctypes.c_int()
                glCreateVertexArrays(1, vao_ptr)
                self._dummy_vao = vao_ptr.value

            # Upload the queued things to draw to the GPU
            # Reallocate buffer if needed
            if data_size > self._ubo_capacity:
                ubo_ptr = ctypes.c_int()
                if self._ubo is not None:
                    ubo_ptr = self._ubo
                    glDeleteBuffers(1, ubo_ptr)
                glCreateBuffers(1, ubo_ptr)
                self._ubo = ubo_ptr.value
                self._ubo_capacity = data_size
                
                glNamedBufferStorage(
                    self._ubo,
                    data_size,
                    data,
                    GL_DYNAMIC_STORAGE_BIT,
                )
            else:
                glNamedBufferSubData(self._ubo, 0, data_size, data)

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            glUseProgram(
                _get_draw_multi_numbers_program()
            )
            glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 0, self._ubo, 0, data_size)
            glBindVertexArray(self._dummy_vao)
            glDrawArrays(GL_TRIANGLES, 0, 6 * count)

            glDisable(GL_BLEND)
            glEnable(GL_DEPTH_TEST)
