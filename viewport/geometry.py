import ctypes

import numpy

from OpenGL.GL import *

__all__ = ("StaticGeometry", "StaticCombinedGeometry")


class StaticGeometry(object):

    def __init__(self, vertex_attrib_sizes, indices, vertices):
        """Initializer.

        vertex_attrib_sizes (tuple): Sizes of float vertices.
            i.e:
                P, UV = (3, 2)
                P, N, UV = (3, 3, 2)
        """
        vertex_float_count = sum(vertex_attrib_sizes)
        self.vertex_attrib_sizes = vertex_attrib_sizes

        self._cleanup = False
        assert(indices.ravel().itemsize == 4)
        assert(vertices.ravel().itemsize == 4)
        assert(len(indices.ravel()) % 3 == 0)
        assert(len(vertices.ravel()) % vertex_float_count == 0)

        self._vbo_ibo_ptr = (ctypes.c_long * 2)()
        self._vao_ptr = ctypes.c_long()
        glCreateBuffers(2, self._vbo_ibo_ptr)
        glCreateVertexArrays(1, self._vao_ptr)
        
        self._cleanup = True

        # Move directly to the GPU (in theory)
        self._vbo = self._vbo_ibo_ptr[0]
        self._ibo = self._vbo_ibo_ptr[1]
        self._vao = self._vao_ptr.value
        vertices_bytes = vertices.tobytes()
        indices_bytes = indices.tobytes()
        glNamedBufferStorage(self._vbo, len(vertices_bytes), vertices_bytes, 0)
        glNamedBufferStorage(self._ibo, len(indices_bytes), indices_bytes, 0)

        # Setup the VAO
        glVertexArrayVertexBuffer(self._vao, 0, self._vbo, 0, 4*vertex_float_count)
        glVertexArrayElementBuffer(self._vao, self._ibo)

        offset = 0
        for idx, count in enumerate(vertex_attrib_sizes):
            glEnableVertexArrayAttrib(self._vao, idx)
            glVertexArrayAttribFormat(self._vao, idx, count, GL_FLOAT, GL_FALSE, offset)
            glVertexArrayAttribBinding(self._vao, idx, 0)
            offset += 4 * count

        self.index_count = len(indices.ravel())

    def bind(self):
        glBindVertexArray(self._vao)

    def draw(self):
        glBindVertexArray(self._vao)
        glDrawElements(GL_TRIANGLES, self.index_count, GL_UNSIGNED_INT, None)

    def __del__(self):
        """Cleanup data."""
        if self._cleanup:
            glDeleteVertexArrays(1, self._vao_ptr)
            glDeleteBuffers(2, self._vbo_ibo_ptr)


class StaticCombinedGeometry(object):
    """Static geometry that shares the safe buffer."""

    def __init__(self, vertex_attrib_sizes, indices_vertices_pairs):
        """Initializer.

        vertex_attrib_sizes (tuple): Sizes of float vertices.
            i.e:
                P, UV = (3, 2)
                P, N, UV = (3, 3, 2)

        indices_vertices_pairs (tuple): Pairs of indices and vertices
            to merge together.
        """
        vertex_float_count = sum(vertex_attrib_sizes)
        self.vertex_attrib_sizes = vertex_attrib_sizes

        self._cleanup = False
        combined_indices = numpy.concatenate([
            indices_vertices[0]
            for indices_vertices in indices_vertices_pairs
        ])
        combined_vertices = numpy.concatenate([
            indices_vertices[1]
            for indices_vertices in indices_vertices_pairs
        ])

        # Data for indirect calls
        counts = numpy.array([
            len(indices_vertices[1].flat)
            for indices_vertices in indices_vertices_pairs
        ], dtype=numpy.uint32)

        first_indexs = numpy.cumsum(
            (
                [0] + [len(indices_vertices[0].flat) for indices_vertices in indices_vertices_pairs]
            )[:-1],
            dtype=numpy.uint32
        )

        base_vertexs = numpy.cumsum(
            (
                [0] + [len(indices_vertices[1].flat)//vertex_float_count for indices_vertices in indices_vertices_pairs]
            )[:-1],
            dtype=numpy.uint32
        )

        assert(combined_indices.ravel().itemsize == 4)
        assert(combined_vertices.ravel().itemsize == 4)
        assert(len(combined_indices.ravel()) % 3 == 0)
        assert(len(combined_vertices.ravel()) % vertex_float_count == 0)

        # Really we could be storing these in the same buffer
        self._buffers = (ctypes.c_long * 4)()
        self._vao_ptr = ctypes.c_long()
        glCreateBuffers(4, self._buffers)
        glCreateVertexArrays(1, self._vao_ptr)

        self._cleanup = True

        self._vbo = self._buffers[0]
        self._ibo = self._buffers[1]
        self.draw_commands_object = self._buffers[2]
        self.counts_object = self._buffers[3]
        self._vao = self._vao_ptr.value

        vertices_bytes = combined_vertices.tobytes()
        indices_bytes = combined_indices.tobytes()
        draw_command_bytes = numpy.array([
            [count, 1, first_index, base_vertex, 0]
            for count, first_index, base_vertex in zip(counts, first_indexs, base_vertexs)
        ], dtype=numpy.uint32).tobytes()
        count_bytes = counts.tobytes()

        glNamedBufferStorage(self._vbo, len(vertices_bytes), vertices_bytes, 0)
        glNamedBufferStorage(self._ibo, len(indices_bytes), indices_bytes, 0)
        glNamedBufferStorage(self.draw_commands_object, len(draw_command_bytes), draw_command_bytes, 0)
        glNamedBufferStorage(self.counts_object, len(count_bytes), count_bytes, 0)

        # Setup the VAO
        glVertexArrayVertexBuffer(self._vao, 0, self._vbo, 0, 4*vertex_float_count)
        glVertexArrayElementBuffer(self._vao, self._ibo)

        offset = 0
        for idx, count in enumerate(vertex_attrib_sizes):
            glEnableVertexArrayAttrib(self._vao, idx)
            glVertexArrayAttribFormat(self._vao, idx, count, GL_FLOAT, GL_FALSE, offset)
            glVertexArrayAttribBinding(self._vao, idx, 0)
            offset += 4 * count

        self.index_counts = counts

    def bind(self):
        glBindVertexArray(self._vao)
        glBindBuffer(GL_DRAW_INDIRECT_BUFFER, self.draw_commands_object)

    def draw(self):
        glBindVertexArray(self._vao)
        glBindBuffer(GL_DRAW_INDIRECT_BUFFER, self.draw_commands_object)
        glMultiDrawElementsIndirect(GL_TRIANGLES, GL_UNSIGNED_INT, None, len(self.index_counts), 0)

    def __del__(self):
        """Cleanup data."""
        if self._cleanup:
            glDeleteVertexArrays(1, self._vao_ptr)
            glDeleteBuffers(4, self._buffers)
