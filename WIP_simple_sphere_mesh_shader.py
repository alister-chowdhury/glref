# FIXME: Theres a weird hole occuring


from math import cos, sin, pi

import numpy

from OpenGL.GL import *
from OpenGL.GL.NV.mesh_shader import *

import viewport


MESH_SHADER_SOURCE = """
#version 460

#extension GL_NV_mesh_shader : require


layout(local_size_x = 32) in;
layout(triangles, max_vertices = 128, max_primitives = 256) out;


layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 modelViewProjection;
layout(location = 2) uniform mat4 inverseTransposeModel;



out VsOut
{
    vec3 P;
    vec3 N;
    vec2 uv;
} vsout[];



#define TWOPI 6.28318530717958647692528676656
#define PI    3.14159265358979323846264338328


#define uCounts 4
#define vCounts 4

void main()
{
    const uint tid = gl_GlobalInvocationID.x;
    gl_PrimitiveCountNV = uCounts * vCounts * 2;
    // vertex count = (uCounts+1) * (vCounts+1);

    // Add vertex
    if(tid < (uCounts+1)*(vCounts+1))
    {
        const float uid = float(tid % (uCounts+1));
        const float vid = float(tid / (uCounts+1));

        const vec2 uv = vec2(uid, vid) / vec2(float(uCounts), float(vCounts));

        float theta = uv.x * PI;
        float phi = uv.y * TWOPI;

        vec4 N = vec4(
            normalize(vec3(
                sin(theta) * cos(phi),
                sin(theta) * sin(phi),
                cos(theta)
            )),
            1.0
        );

        gl_MeshVerticesNV[tid].gl_Position = modelViewProjection * N;

        vec4 P = model * N;
             P.xyz /= P.w;

        N = inverseTransposeModel * N;
             N.xyz /= P.w;

        vsout[tid].P = P.xyz;
        vsout[tid].N = N.xyz;
        vsout[tid].uv = uv.yx;

    }


    // Add quad
    if(tid < (uCounts*vCounts))
    {
        uint vindex = tid;

        gl_PrimitiveIndicesNV[6*tid+0] = vindex;
        gl_PrimitiveIndicesNV[6*tid+1] = vindex+1;
        gl_PrimitiveIndicesNV[6*tid+2] = vindex+1 + (uCounts+1);

        gl_PrimitiveIndicesNV[6*tid+3] = vindex;
        gl_PrimitiveIndicesNV[6*tid+4] = vindex+1 + (uCounts+1);
        gl_PrimitiveIndicesNV[6*tid+5] = vindex   + (uCounts+1);
    }

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
        case 1: outRgba = vec4(normalize(N), 1.0); break;
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

        self._sphere_model = numpy.matrix([
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
        glUniformMatrix4fv(0, 1, GL_FALSE, self._sphere_model.flatten())
        glUniformMatrix4fv(1, 1, GL_FALSE, (self._sphere_model * self.camera.view_projection).flatten())
        glUniformMatrix4fv(2, 1, GL_FALSE, (self._sphere_model.T.I.flatten()))
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




