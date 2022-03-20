import os
import numpy
from OpenGL.GL import *

from viewport import make_permutation_program, get_dummy_vao


_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DEBUG_DRAW_CARDS = make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER=os.path.join(_SHADER_DIR, "draw_cards.vert"),
    GL_FRAGMENT_SHADER=os.path.join(_SHADER_DIR, "draw_cards.frag"),
)

_DEBUG_DRAW_COMPACT_BBOX = make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER=os.path.join(_SHADER_DIR, "draw_compact_bbox.vert"),
    GL_FRAGMENT_SHADER=os.path.join(_SHADER_DIR, "draw_compact_bbox.frag"),
)


class Card(object):

    def __init__(
            self,
            axis_x=None,
            axis_y=None,
            axis_z=None,
            origin=None,
            local_extent=None
    ):
        self.axis_x = axis_x
        self.axis_y = axis_y
        self.axis_z = axis_z
        self.origin = origin
        self.local_extent = local_extent


    def pack(self):
        data = numpy.zeros(16, dtype=numpy.float32)
        data[0:3] = self.axis_x
        data[3] = self.origin[0]
        data[4:7] = self.axis_y
        data[7] = self.origin[1]
        data[8:11] = self.axis_z
        data[11] = self.origin[2]
        data[12:15] = self.local_extent
        return data.tobytes()


class CardBuffer(object):

    def __init__(self, cards):
        self.cards = cards
        self.num_cards = len(cards)
        self.ssbo = None

        card_data = b''
        for card in cards:
            card_data += card.pack()

        self.ssbo_size = len(card_data)
        ssbo_ptr = ctypes.c_int()
        glCreateBuffers(1, ssbo_ptr)
        self.ssbo = ssbo_ptr.value

        glNamedBufferStorage(
            self.ssbo,
            self.ssbo_size,
            card_data,
            0,
        )


    @classmethod
    def load_from_file(cls, filepath):
        with open(filepath, "rb") as in_fp:
            data = numpy.frombuffer(in_fp.read(), dtype=numpy.float32)
        cards = []
        for idx in range(0, len(data), 15):
            axis_x = data[idx:idx+3]
            axis_y = data[idx+3:idx+6]
            axis_z = data[idx+6:idx+9]
            origin = data[idx+9:idx+12]
            local_extent = data[idx+12:idx+15]
            cards.append(Card(
                axis_x = axis_x,
                axis_y = axis_y,
                axis_z = axis_z,
                origin = origin,
                local_extent = local_extent,
            ))
        return cls(cards)


    def __del__(self):
        if self.ssbo is not None:
            glDeleteBuffers(1, self.ssbo)


    def bind(self, binding_id=0):
        glBindBufferRange(
            GL_SHADER_STORAGE_BUFFER,
            binding_id,
            self.ssbo,
            0,
            self.ssbo_size
        )


    def debug_draw(self, view_projection):
        glBindVertexArray(get_dummy_vao())
        glUseProgram(_DEBUG_DRAW_CARDS.one())
        glUniformMatrix4fv(0, 1, GL_FALSE, view_projection.flatten())
        self.bind(0)
        glDrawArrays(GL_TRIANGLES, 0, 6 * self.num_cards)

    def debug_compact_bbox(self, compact_bbox, view_projection):
        glBindVertexArray(get_dummy_vao())
        glUseProgram(_DEBUG_DRAW_COMPACT_BBOX.one())
        glUniformMatrix4fv(0, 1, GL_FALSE, view_projection.flatten())
        glBindImageTexture(0, compact_bbox, 0, 0, 0, GL_READ_ONLY, GL_RGBA32F)
        glDrawArrays(GL_LINES, 0, 24 * self.num_cards)
