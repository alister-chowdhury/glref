# So, atleast on my machine, my intel onboard gfx card seems to do something funky with gl_DrawID and with
# gl_GlobalInvocationID.x and basically doesn't seem to work unless you do some weird stuff in the fragment
# shader.
# Seems to work as expect on my NVIDIA card.

from math import cos, sin, pi

import numpy

from OpenGL.GL import *

import viewport


VERTEX_SHADER_SOURCE = """
#version 460 core

readonly layout(std430, binding = 0) buffer models_ { mat4 models[];};
layout(location = 0) uniform mat4 viewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;

layout(location = 0) out vec3 out_P;
layout(location = 1) out vec2 out_uv;

void main() {
    mat4 model = models[gl_DrawID];
    vec4 world_p = model * vec4(P, 1.0);
    out_P = world_p.xyz / world_p.w;
    out_uv = uv;
    gl_Position = (viewProjection * model) * vec4(P, 1.0);
    gl_Position /= gl_Position.w;
}
"""

FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 1) uniform vec3 light;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;


layout(location = 0) out vec4 outRgba;

void main() {
    vec3 dx = dFdx(P);
    vec3 dy = dFdy(P);
    float l = dot(normalize(cross(dx, dy)), normalize(light-P));
    outRgba = vec4(uv, abs(l), 1.0);
}
"""


FRUSTUM_CULLING_SOURCE = """
#version 460 core

layout(local_size_x=1) in;


layout(location = 0) uniform mat4 viewProjection;
readonly layout(std430, binding = 0) buffer models_ { mat4 models[];};

/*
    typedef  struct {
        uint  count;
        uint  instanceCount;
        uint  firstIndex;
        uint  baseVertex;
        uint  baseInstance;
    } DrawElementsIndirectCommand;
*/
writeonly layout(std430, binding = 1) buffer draw_elements_command_ { uint draw_elements_command[];};

/*
    typedef  struct {
        vec4  mins, maxs;
    } BBox3d;
*/
readonly layout(std430, binding = 2) buffer bboxs_ { vec4 bboxs[];};
readonly layout(std430, binding = 3) buffer counts_ { uint counts[];};


void main() {
    
    uint idx = gl_GlobalInvocationID.x;
    mat4 mvp = viewProjection * models[idx];

    vec4 bboxA = bboxs[2*idx];
    vec4 bboxB = bboxs[2*idx+1];

    mat4 bboxBlockA = mvp * mat4(
        bboxA,
        vec4(bboxA.x, bboxB.yzw),
        vec4(bboxA.xy, bboxB.zw),
        vec4(bboxA.x, bboxB.y, bboxA.zw)
    );
    bboxBlockA[0] /= bboxBlockA[0].w;
    bboxBlockA[1] /= bboxBlockA[1].w;
    bboxBlockA[2] /= bboxBlockA[2].w;
    bboxBlockA[3] /= bboxBlockA[3].w;

    mat4 bboxBlockB = mvp * mat4(
        bboxB,
        vec4(bboxB.x, bboxA.yzw),
        vec4(bboxB.xy, bboxA.zw),
        vec4(bboxB.x, bboxA.y, bboxB.zw)
    );
    bboxBlockB[0] /= bboxBlockB[0].w;
    bboxBlockB[1] /= bboxBlockB[1].w;
    bboxBlockB[2] /= bboxBlockB[2].w;
    bboxBlockB[3] /= bboxBlockB[3].w;

    vec3 xyz_mins = min(
        min(min(bboxBlockA[0].xyz, bboxBlockA[1].xyz), min(bboxBlockA[2].xyz, bboxBlockA[3].xyz)),
        min(min(bboxBlockB[0].xyz, bboxBlockB[1].xyz), min(bboxBlockB[2].xyz, bboxBlockB[3].xyz))
    );
    vec3 xyz_maxs = max(
        max(max(bboxBlockA[0].xyz, bboxBlockA[1].xyz), max(bboxBlockA[2].xyz, bboxBlockA[3].xyz)),
        max(max(bboxBlockB[0].xyz, bboxBlockB[1].xyz), max(bboxBlockB[2].xyz, bboxBlockB[3].xyz))
    );

    bool cull = any(bvec3(
        uvec3(lessThan(xyz_maxs, vec3(-1.0)))
        | uvec3(greaterThan(xyz_mins, vec3(1.0)))
    ));

    // Set the count to 0 if we want to cull it
    draw_elements_command[5*idx] = cull ? 0 : counts[idx];
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

        self.cubes = None

        self._buffer_objects = None
        self._bboxes = None
        self._models = None

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        def make_puv_offset(arr, x, y, z, sx=1, sy=1, sz=1):
            arr = numpy.array(arr)
            arr[0::5] *= sx
            arr[0::5] += x
            arr[1::5] *= sy
            arr[1::5] += y
            arr[2::5] *= sz
            arr[2::5] += z
            return arr

        geo = [
                (viewport.CUBE_INDICES, viewport.PUV_CUBE_VERTICES),
                #
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 2, 0, 0.5, 0.5, 0.5)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 2, 0, 0, 0.5, 0.5, 0.5)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 0, 2, 0.5, 0.5, 0.5)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 0, -2, 0.5, 0.5, 0.5)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, -2, 0, 0, 0.5, 0.5, 0.5)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 3, 0, 0.25, 0.25, 0.25)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 3, 0, 0, 0.25, 0.25, 0.25)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 0, 3, 0.25, 0.25, 0.25)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 0, -3, 0.25, 0.25, 0.25)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, -3, 0, 0, 0.25, 0.25, 0.25)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 3.5, 0, 0.125, 0.125, 0.125)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 3.5, 0, 0, 0.125, 0.125, 0.125)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 0, 3.5, 0.125, 0.125, 0.125)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, 0, 0, -3.5, 0.125, 0.125, 0.125)),
                (viewport.CUBE_INDICES, make_puv_offset(viewport.PUV_CUBE_VERTICES, -3.5, 0, 0, 0.125, 0.125, 0.125)),
        ]

        self.cubes = viewport.StaticCombinedGeometry(
            (3, 2), # P, UV
            geo
        )

        # Generate model matrices and bboxes
        self._buffer_objects = (ctypes.c_long * 2)()
        glCreateBuffers(2, self._buffer_objects)
        self._bboxes = self._buffer_objects[0]
        self._models = self._buffer_objects[1]

        def make_bbox(puv_vertices):
            v = puv_vertices.reshape(len(puv_vertices.flat)//5, 5)
            mins = v.min(axis=0)
            maxs = v.max(axis=0)
            return [mins[0], mins[1], mins[2], 1.0, maxs[0], maxs[1], maxs[2], 1.0]

        bbox_bytes = numpy.array([
            make_bbox(pair[1])
            for pair in geo
        ], dtype=numpy.float32).tobytes()

        models_bytes = numpy.array([
            [
                [1+i*0.1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [i*0.1, 0, 0, 1],
            ]
            for i in range(len(geo))
        ], dtype=numpy.float32).tobytes()


        glNamedBufferStorage(self._bboxes, len(bbox_bytes), bbox_bytes, 0)
        glNamedBufferStorage(self._models, len(models_bytes), models_bytes, 0)

        self._draw_uvs_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=FRAGMENT_SHADER_SOURCE
        )

        self._cull_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=FRUSTUM_CULLING_SOURCE
        )

        self.camera.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self._cull_program)

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._models)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.cubes.draw_commands_object)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._bboxes)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self.cubes.counts_object)
        glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.view_projection.flatten())

        glDispatchCompute(len(self.cubes.index_counts), 1, 1)
        glMemoryBarrier(GL_COMMAND_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(self._draw_uvs_program)
        glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.view_projection.flatten())
        glUniform3f(1, self.camera.eye[0], self.camera.eye[1], self.camera.eye[2])
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._models)        
        self.cubes.draw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)

    def _keypress(self, wnd, key, x, y):
        # Move the camera
        if key == b'w':
            self.camera.move(numpy.array([0, 1, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))
        elif key == b's':
            self.camera.move(numpy.array([0, -1, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))

        elif key == b'a':
            self.camera.move(numpy.array([1, 0, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))
        elif key == b'd':
            self.camera.move(numpy.array([-1, 0, 0]))
            self.camera.look_at(numpy.array([0, 0, 0]))

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # No redraw
        else:
            return

        wnd.redraw()

    def _drag(self, wnd, x, y):
        deriv_u = x / wnd.width * 20
        deriv_v = y / wnd.height * -20

        view = self.camera.view

        X = numpy.array(view.T[0]).flatten()[0:3] * deriv_u
        Y = numpy.array(view.T[1]).flatten()[0:3] * deriv_v

        self.camera.move(X + Y)

        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()

