from math import cos, sin, pi

import numpy

from OpenGL.GL import *
from OpenGL.GL.NV.mesh_shader import *

import viewport


MESH_SHADER_SOURCE = """
#version 460

#extension GL_NV_mesh_shader : require


layout(local_size_x = 12) in;
layout(triangles, max_vertices = 36, max_primitives = 12) out;


layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 modelViewProjection;
layout(location = 2) uniform mat4 inverseTransposeModel;


const uvec3 indices[12] = uvec3[12](
    // front
    uvec3(0, 1, 2), uvec3(2, 3, 0),
    // top
    uvec3(1, 5, 6), uvec3(6, 2, 1),
    // back
    uvec3(7, 6, 5), uvec3(5, 4, 7),
    // bottom
    uvec3(4, 0, 3), uvec3(3, 7, 4),
    // left
    uvec3(4, 5, 1), uvec3(1, 0, 4),
    // right
    uvec3(3, 2, 6), uvec3(6, 7, 3)
);

const vec3 positions[8] = vec3[8](
    // front
    vec3(-1.0,  -1.0,  1.0), vec3(1.0,   -1.0,  1.0),
    vec3(1.0,   1.0,   1.0), vec3(-1.0,  1.0,   1.0),
    // back
    vec3(-1.0,  -1.0, -1.0), vec3(1.0,   -1.0, -1.0),
    vec3(1.0,   1.0,  -1.0), vec3(-1.0,  1.0,  -1.0)
);


const vec2 uvs[4] = vec2[4](
    vec2(0.0, 0.0), vec2(1.0, 0.0),
    vec2(1.0, 1.0), vec2(0.0, 1.0)
);


out VsOut
{
    vec3 P;
    vec3 N;
    vec2 uv;
} vsout[];



vec3 applyModelMatrix(vec3 P)
{
    vec4 Pprime = model * vec4(P, 1.0);
    return Pprime.xyz / Pprime.z;
}


void main()
{
    const uint tid = gl_GlobalInvocationID.x;

    gl_PrimitiveCountNV = 12;
    uvec3 triangleIndices = indices[tid];

    vec3 Pa = positions[triangleIndices.x];
    vec3 Pb = positions[triangleIndices.y];
    vec3 Pc = positions[triangleIndices.z];

    vec3 N = (inverseTransposeModel * vec4(normalize(cross(Pb-Pa, Pc-Pa)), 1.0)).xyz;

    vsout[tid*3].P = applyModelMatrix(Pa);
    vsout[tid*3].N = N;
    vsout[tid*3].uv = uvs[triangleIndices.x & 3];

    vsout[tid*3+1].P = applyModelMatrix(Pb);
    vsout[tid*3+1].N = N;
    vsout[tid*3+1].uv = uvs[triangleIndices.y & 3];

    vsout[tid*3+2].P = applyModelMatrix(Pc);
    vsout[tid*3+2].N = N;
    vsout[tid*3+2].uv = uvs[triangleIndices.z & 3];

    gl_MeshVerticesNV[3*tid].gl_Position = modelViewProjection * vec4(Pa, 1.0);
    gl_MeshVerticesNV[3*tid+1].gl_Position = modelViewProjection * vec4(Pb, 1.0);
    gl_MeshVerticesNV[3*tid+2].gl_Position = modelViewProjection * vec4(Pc, 1.0);

    gl_PrimitiveIndicesNV[3*tid] = 3*tid;
    gl_PrimitiveIndicesNV[3*tid+1] = 3*tid+1;
    gl_PrimitiveIndicesNV[3*tid+2] = 3*tid+2;

}

"""

FRAGMENT_SHADER_SOURCE = """
#version 460

layout(location = 3) uniform uint displayMode;


in VsOut
{
    vec3 P;
    vec3 N;
    vec2 uv;
};


layout(location = 0) out vec4 outRgba;


void main() {
    switch(displayMode)
    {
        case 0: outRgba = vec4(P, 1.0); break;
        case 1: outRgba = vec4(N, 1.0); break;
        case 2: outRgba = vec4(uv, 0.0, 1.0); break;
    }
}
"""

class Renderer(object):


    def __init__(self):

        self.window = viewport.Window()
        self.camera = viewport.Camera()

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress
        self.window.on_idle = lambda x: x.redraw()

        self.cube = None
        # Default to drawing position
        self.display_mode = 0

    def run(self):
        self.window.run()

    def _init(self, wnd):
        if not viewport.has_gl_extension("GL_NV_mesh_shader"):
            raise RuntimeError("Mesh shaders not supported by GPU.")

        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self._cube_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=numpy.float32)
        
        self._draw_cube_program = viewport.generate_shader_program(
            GL_MESH_SHADER_NV=MESH_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=FRAGMENT_SHADER_SOURCE
        )

        self.camera.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )

        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self._draw_cube_program)
        glUniformMatrix4fv(0, 1, GL_FALSE, self._cube_model.flatten())
        glUniformMatrix4fv(1, 1, GL_FALSE, (self._cube_model * self.camera.view_projection).flatten())
        glUniformMatrix4fv(2, 1, GL_FALSE, (self._cube_model.T.I.flatten()))
        glUniform1ui(3, self.display_mode)
        glDrawMeshTasksNV(0, 1)


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)


    def _keypress(self, wnd, key, x, y):
        # Move the camera
        if key == b'w':
            self.camera.move_local(numpy.array([0, 0, 1]))
        elif key == b's':
            self.camera.move_local(numpy.array([0, 0, -1]))

        elif key == b'a':
            self.camera.move_local(numpy.array([1, 0, 0]))
        elif key == b'd':
            self.camera.move_local(numpy.array([-1, 0, 0]))

        elif key == b'q':
            self.camera.move_local(numpy.array([0, 1, 0]))
        elif key == b'e':
            self.camera.move_local(numpy.array([0, -1, 0]))

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        elif key == b'p':
            self.display_mode = 0
        elif key == b'n':
            self.display_mode = 1
        elif key == b'u':
            self.display_mode = 2

        # No redraw
        else:
            return

        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height

        sin_u = sin(deriv_u * pi)
        cos_u = cos(deriv_u * pi)
        sin_v = sin(deriv_v * pi)
        cos_v = cos(deriv_v * pi)

        ortho = self.camera.orthonormal_basis
        
        # Y
        M = numpy.matrix([
            [cos_u, 0, sin_u],
            [0, 1, 0],
            [-sin_u, 0, cos_u],
        ])

        # XY stuff
        if button == wnd.RIGHT:
            N = numpy.matrix([
                [cos_v, -sin_v, 0],
                [sin_v, cos_v, 0],
                [0, 0, 1],
            ])
            N = ortho * N * ortho.I
        else:
            N = numpy.matrix([
                [1, 0, 0],
                [0, cos_v, -sin_v],
                [0, sin_v, cos_v],
            ])
            N = ortho * N * ortho.I
        M *= N

        self.camera.append_3x3_transform(M)

        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()




