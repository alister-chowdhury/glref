import ctypes

from OpenGL.GL import *

__all__ = ("StaticGeometry",)


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
        self._cleanup = True

        self._vbo_ibo_ptr = (ctypes.c_long * 2)()
        self._vao_ptr = ctypes.c_long()
        glCreateBuffers(2, self._vbo_ibo_ptr)
        glCreateVertexArrays(1, self._vao_ptr)

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
