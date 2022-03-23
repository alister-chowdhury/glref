import os
import ctypes

import numpy
from OpenGL.GL import *

from viewport import make_permutation_program


_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)


_GENERATE_COMPACT_CARDS = make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER=os.path.join(_SHADER_DIR, "generate_compact_cards.comp")
)


def generate_compact_cards(card_buffer):

    dim = card_buffer.num_cards

    textures = (ctypes.c_int * 2)()
    glCreateTextures(GL_TEXTURE_1D, 2, textures)

    for i in range(2):
        glTextureParameteri(textures[i], GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(textures[i], GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(textures[i], GL_TEXTURE_MAG_FILTER, GL_NEAREST)    

    origins = textures[0]
    bboxs = textures[1]

    glTextureStorage1D(origins, 1, GL_RGBA32F, dim)
    glTextureStorage1D(bboxs, 1, GL_RGBA32F, dim * 2)

    glUseProgram(_GENERATE_COMPACT_CARDS.one())

    glUniform1ui(0, card_buffer.num_cards)
    glBindImageTexture(0, origins, 0, 0, 0, GL_WRITE_ONLY, GL_RGBA32F)
    glBindImageTexture(1, bboxs, 0, 0, 0, GL_WRITE_ONLY, GL_RGBA32F)
    card_buffer.bind(2)
    glDispatchCompute((card_buffer.num_cards + 63)//64, 1, 1)

    return origins, bboxs


class PythonBVHCard(object):

    def __init__(self, card, card_index):
        self.card_index = card_index
        offset = (
            numpy.array(card.origin)
            + numpy.array(card.axis_z) * card.local_extent[2]
        )
        X = numpy.array(card.axis_x) * card.local_extent[0]
        Y = numpy.array(card.axis_y) * card.local_extent[1]
        p0 =  X - Y
        p1 =  X + Y
        p2 = -X - Y
        p3 = -X + Y
        self.bbox_min = numpy.minimum(
            numpy.minimum(p0, p1),
            numpy.minimum(p2, p3)
        ) + offset
        self.bbox_max = numpy.maximum(
            numpy.maximum(p0, p1),
            numpy.maximum(p2, p3)
        ) + offset
        self.center = (self.bbox_min + self.bbox_max) * 0.5


def generate_bvh_python_subdivde(cards, index, allocator, data_stream, debug_bboxes):
    centers = [card.center for card in cards]
    extent_min = numpy.min(centers, axis=0)
    extent_max = numpy.max(centers, axis=0)
    split_w = (extent_min + extent_max) * 0.5
    delta = extent_max - extent_min
    split_plane = None
    if delta[0] > delta[1]:
        if delta[0] > delta[2]:
            split_plane = numpy.array((1, 0, 0))
        else:
            split_plane = numpy.array((0, 0, 1))
    elif delta[1] > delta[2]:
        split_plane = numpy.array((0, 1, 0))
    else:
        split_plane = numpy.array((0, 0, 1))
    sides = (numpy.dot(centers, split_plane) - numpy.dot(split_w, split_plane)) > 0
    
    left = cards[sides]
    if len(left):
        left_bbox_min = numpy.min([card.bbox_min for card in left], axis=0)
        left_bbox_max = numpy.max([card.bbox_max for card in left], axis=0)
    else:
        left_bbox_min = numpy.array([1e+35, 1e+35, 1e+35])
        left_bbox_max = numpy.array([-1e+35, -1e+35, -1e+35])

    # Node
    left_type = 0
    left_index = allocator[0]
    
    if len(left) <= 4:
        left_type = 1
        allocator[0] += 1
        indices = [0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff]
        for i, k  in enumerate(left):
            indices[i] = k.card_index
        data_stream.extend(indices)
    else:
        allocator[0] += 4
        data_stream.extend((0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        generate_bvh_python_subdivde(left, left_index, allocator, data_stream, debug_bboxes)
    
    right = cards[~sides]
    if len(right):
        right_bbox_min = numpy.min([card.bbox_min for card in right], axis=0)
        right_bbox_max = numpy.max([card.bbox_max for card in right], axis=0)
    else:
        right_bbox_min = numpy.array([1e+35, 1e+35, 1e+35])
        right_bbox_max = numpy.array([-1e+35, -1e+35, -1e+35])

    right_type = 0
    right_index = allocator[0]
    
    if len(right) <= 4:
        right_type = 1
        allocator[0] += 1
        indices = [0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff]
        for i, k  in enumerate(right):
            indices[i] = k.card_index
        data_stream.extend(indices)
    else:
        allocator[0] += 4
        data_stream.extend((0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        generate_bvh_python_subdivde(right, right_index, allocator, data_stream, debug_bboxes)

    if(all(x < y for x, y in zip(left_bbox_min, left_bbox_max))):
        debug_bboxes.extend((left_bbox_min[0], left_bbox_min[1], left_bbox_min[2], 0))
        debug_bboxes.extend((left_bbox_max[0], left_bbox_max[1], left_bbox_max[2], 0))
    if(all(x < y for x, y in zip(right_bbox_min, right_bbox_max))):
        debug_bboxes.extend((right_bbox_min[0], right_bbox_min[1], right_bbox_min[2], 0))
        debug_bboxes.extend((right_bbox_max[0], right_bbox_max[1], right_bbox_max[2], 0))

    output_offset = index * 4
    V0xyz = numpy.frombuffer(numpy.array(left_bbox_min, dtype=numpy.float32), dtype=numpy.uint32)
    V1xyz = numpy.frombuffer(numpy.array(left_bbox_max, dtype=numpy.float32), dtype=numpy.uint32)
    V2xyz = numpy.frombuffer(numpy.array(right_bbox_min, dtype=numpy.float32), dtype=numpy.uint32)
    V3xyz = numpy.frombuffer(numpy.array(right_bbox_max, dtype=numpy.float32), dtype=numpy.uint32)
    data_stream[output_offset + 0] = V0xyz[0]
    data_stream[output_offset + 1] = V0xyz[1]
    data_stream[output_offset + 2] = V0xyz[2]
    data_stream[output_offset + 3] = left_type
    data_stream[output_offset + 4] = V1xyz[0]
    data_stream[output_offset + 5] = V1xyz[1]
    data_stream[output_offset + 6] = V1xyz[2]
    data_stream[output_offset + 7] = left_index
    data_stream[output_offset + 8] = V2xyz[0]
    data_stream[output_offset + 9] = V2xyz[1]
    data_stream[output_offset + 10] = V2xyz[2]
    data_stream[output_offset + 11] = right_type
    data_stream[output_offset + 12] = V3xyz[0]
    data_stream[output_offset + 13] = V3xyz[1]
    data_stream[output_offset + 14] = V3xyz[2]
    data_stream[output_offset + 15] = right_index





def generate_bvh_python(card_buffer):
    card_nodes = numpy.array([
        PythonBVHCard(card, i) for i, card in enumerate(card_buffer.cards)
    ])
    allocator = [4]
    data_stream = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    debug_bboxes = []
    generate_bvh_python_subdivde(card_nodes, 0, allocator, data_stream, debug_bboxes)
    return data_stream, debug_bboxes



