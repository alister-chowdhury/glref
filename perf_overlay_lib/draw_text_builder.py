import os
import struct

import numpy
from OpenGL.GL import *

from viewport import load_shader_source, generate_shader_program, get_dummy_vao

_FONT_DAT_PATH = os.path.abspath(
    os.path.join(
        __file__,
        "..",
        "..",
        "data",
        "generate_binary_utf_bmp_map",
        "output",
        # "miniwi-8-modified.dat"
        "BmPlus_ToshibaSat_9x16.dat"
    )
)

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DRAW_MULTI_TEXT_VERT_PATH = os.path.join(
    _SHADER_DIR, "draw_multi_text.vert"
)

_DRAW_TEXT_FRAG_PATH = os.path.join(
    _SHADER_DIR, "draw_text.frag"
)

_DRAW_MULTI_TEXT_PROGRAMS = {}


def _get_draw_multi_text_program(ascii_input=False):
    key = (ascii,)
    if key not in _DRAW_MULTI_TEXT_PROGRAMS:
        _DRAW_MULTI_TEXT_PROGRAMS[key] = generate_shader_program(
            GL_VERTEX_SHADER=load_shader_source(_DRAW_MULTI_TEXT_VERT_PATH),
            GL_FRAGMENT_SHADER=load_shader_source(
                _DRAW_TEXT_FRAG_PATH,
                macros={"ASCII": int(ascii_input)}
            )
        )
    return _DRAW_MULTI_TEXT_PROGRAMS[key]



class DrawTextBuilder(object):

    def __init__(self):
        self._ubo = None
        self._ubo_capacity = 0
        self._font_data_size = 0
        self._font_ubo = None
        self._ascii_queue = []
        self._utf16_queue = []

    def __del__(self):
        if self._ubo is not None:
            ubo_ptr = self._ubo
            glDeleteBuffers(1, ubo_ptr)
        if self._font_ubo is not None:
            ubo_ptr = self._font_ubo
            glDeleteBuffers(1, ubo_ptr)

    @staticmethod
    def _collapse_queue(queue):
        headers = numpy.array([
            entry[0]
            for entry in queue
        ])

        # Make text data a single stream of u32s
        text_data = numpy.array([
            c
            for entry in queue
            for c in entry[1]
        ], dtype=numpy.uint32)

        global_offset = headers.nbytes >> 2
        for i, entry in enumerate(queue):
            headers[i, 4] = global_offset
            global_offset += len(entry[1])

        return headers.tobytes() + text_data.tobytes()

    def add(self, characters, bounds, bg_col, fg_col):
        text_data = numpy.array([ord(c) for c in characters])
        is_ascii = (text_data < 256).all()

        if is_ascii:
            text_data = text_data.astype(numpy.uint8)
            aligned_size = ((len(text_data) - 1) | 3) + 1
            if aligned_size != len(text_data):
                text_data.resize(aligned_size, refcheck=False)
            text_data = text_data.view("<I")

        else:
            text_data = text_data.astype(numpy.uint16)
            aligned_size = len(text_data) + (len(text_data) & 1)
            if aligned_size != len(text_data):
                text_data.resize(aligned_size, refcheck=False)
            text_data = text_data.view("<I")

        bounds = struct.pack("ffff", *bounds)
        num_chars = struct.pack("I", len(characters))

        bg_col = (
            numpy.array(bg_col, dtype=numpy.float32)
            * 255
        ).astype(numpy.uint8).tobytes()

        fg_col = (
            numpy.array(fg_col, dtype=numpy.float32)
            * 255
        ).astype(numpy.uint8).tobytes()

        header = (
            bounds
            + b"\x00\x00\x00\x00"
            + num_chars
            + bg_col
            + fg_col
        )
        header = numpy.frombuffer(header, dtype=numpy.uint32)

        if is_ascii:
            self._ascii_queue.append((header, text_data))
        else:
            self._utf16_queue.append((header, text_data))


    def flush(self):
        data = b""
        ascii_size = 0
        unicode_size = 0

        if self._ascii_queue:
            data = self._collapse_queue(
                self._ascii_queue
            )
            ascii_size = len(data)

        if self._utf16_queue:
            utf16_data = self._collapse_queue(
                self._utf16_queue
            )
            unicode_size = len(utf16_data)
            data += utf16_data

        # Upload the queued things to draw to the GPU
        # Reallocate buffer if needed
        if data:
            if len(data) > self._ubo_capacity:
                ubo_ptr = ctypes.c_int()
                if self._ubo is not None:
                    ubo_ptr = self._ubo
                    glDeleteBuffers(1, ubo_ptr)
                glCreateBuffers(1, ubo_ptr)
                self._ubo = ubo_ptr.value
                self._ubo_capacity = len(data)
                
                glNamedBufferStorage(
                    self._ubo,
                    len(data),
                    data,
                    GL_DYNAMIC_STORAGE_BIT,
                )
            else:
                glNamedBufferSubData(self._ubo, 0, len(data), data)

            # Load font data if not already done
            if self._font_ubo is None:
                with open(_FONT_DAT_PATH, "rb") as in_fp:
                    font_data = in_fp.read()
                    self._font_data_size = len(font_data)

                ubo_ptr = ctypes.c_int()
                glCreateBuffers(1, ubo_ptr)
                self._font_ubo = ubo_ptr.value
                glNamedBufferStorage(
                    self._font_ubo,
                    self._font_data_size,
                    font_data,
                    0,
                )

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            if ascii_size:
                count = len(self._ascii_queue)
                self._ascii_queue = []

                glUseProgram(
                    _get_draw_multi_text_program(True)
                )
                glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 0, self._font_ubo, 0, self._font_data_size)
                glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 1, self._ubo, 0, ascii_size)
                glBindVertexArray(get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 6 * count)

            if unicode_size:
                count = len(self._utf16_queue)
                self._utf16_queue = []

                glUseProgram(
                    _get_draw_multi_text_program(False)
                )
                glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 0, self._font_ubo, 0, self._font_data_size)
                glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 1, self._ubo, ascii_size, unicode_size)
                glBindVertexArray(get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 6 * count)

            glDisable(GL_BLEND)
            glEnable(GL_DEPTH_TEST)
