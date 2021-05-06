import ctypes
from enum import Enum

import numpy

from OpenGL.GL import *

try:
    import pywavefront
    _has_pywavefront = True
except ImportError:
    _has_pywavefront = False



__all__ = ("StaticGeometry", "StaticCombinedGeometry", "ObjGeomAttr", "load_obj")


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

        self._vbo_ibo_ptr = (ctypes.c_int * 2)()
        self._vao_ptr = ctypes.c_int()
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
        self._buffers = (ctypes.c_int * 4)()
        self._vao_ptr = ctypes.c_int()
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

        # So while attempting to work around intels gl_DrawID being a bit odd and trying
        # to use: https://www.g-truc.net/post-0518.html
        # Simply enabling an extra attrib magically fixes it for reasons I am unsure of.
        glEnableVertexArrayAttrib(self._vao, len(vertex_attrib_sizes))

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
            glDeleteBuffers(5, self._buffers)


class ObjGeomAttr(Enum):
    UV = 0
    P = 1
    N = 2


_OBJATTR_TO_PYWAVE_VERTEX_FORMAT = {
    ObjGeomAttr.UV: "T2F",
    ObjGeomAttr.P: "V3F",
    ObjGeomAttr.N: "N3F",
}

_OBJATTR_TO_SIZE = {
    ObjGeomAttr.UV: 2,
    ObjGeomAttr.P: 3,
    ObjGeomAttr.N: 3,    
}


def load_obj(obj_filepath, attrs):
    """Load an OBJ into a drawable mesh.

    Args:
        obj_filepath (str): Obj file to stream in.
        attrs (iterable[ObjGeomAttr]): Attributes to read.

    Returns:
        StaticGeometry or StaticCombinedGeometry: Drawable mesh.
    """
    assert _has_pywavefront
    obj_filepath = obj_filepath
    attrs = tuple(attrs)

    scene = pywavefront.Wavefront(obj_filepath)

    mesh_data = []
    for mesh in scene.mesh_list:
        # Not supporting anything fancy here
        material = mesh.materials[0]
        obj_attrs = material.vertex_format.split("_")

        # Figure out where the attributes we care about are
        # located within the obj vertex layout
        obj_attr_offset = 0
        obj_attr_offsets = []
        for obj_attr in obj_attrs:
            obj_attr_offsets.append(obj_attr_offset)
            if obj_attr.endswith("3F"):
                obj_attr_offset += 3
            elif obj_attr.endswith("2F"):
                obj_attr_offset += 2
            else:
                raise RuntimeError(
                    "Unknown pywavefront attr size for {0}"
                    .format(obj_attr)
                )

        obj_vertices = numpy.array(material.vertices, dtype=numpy.float32)
        obj_vertices = obj_vertices.reshape(
            (obj_vertices.size//obj_attr_offset, obj_attr_offset)
        ).T

        # Load arrays of vertices into a list
        # which we will then coallasce at the end
        vertex_data = []

        for attr in attrs:
            obj_attr_name = _OBJATTR_TO_PYWAVE_VERTEX_FORMAT[attr]
            if obj_attr_name not in obj_attrs:
                raise RuntimeError(
                    "Missing attribute on mesh: {0}".format(attr.name)
                )
            obj_attr_offset = obj_attr_offsets[
                obj_attrs.index(obj_attr_name)
            ]
            attr_data = obj_vertices[
                obj_attr_offset:
                obj_attr_offset+_OBJATTR_TO_SIZE[attr]
            ]
            vertex_data.append(attr_data.T)

        # pywavefront doesn't index things and its face collection is pretty useless
        # so we're just going to do it ourselves
        vertex_data = numpy.column_stack(vertex_data)
        vertex_tuples = tuple(map(tuple, vertex_data))
        unique_vertices = tuple(set(vertex_tuples))
        vertex_map = {vertex: index for index, vertex in enumerate(unique_vertices)}

        vertices = numpy.array(unique_vertices, dtype=numpy.float32).ravel()
        indices = numpy.array([vertex_map[vertex] for vertex in vertex_tuples], dtype=numpy.uint32)

        mesh_data.append((indices, vertices))

    vertex_attrib_sizes = [
        _OBJATTR_TO_SIZE[attr]
        for attr in attrs
    ]

    assert len(mesh_data) > 0

    if len(mesh_data) == 1:
        return StaticGeometry(
            vertex_attrib_sizes,
            mesh_data[0][0],
            mesh_data[0][1]
        )

    else:
        return StaticCombinedGeometry(
            vertex_attrib_sizes,
            mesh_data
        )
