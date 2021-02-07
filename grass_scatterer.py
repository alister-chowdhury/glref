from math import cos, sin, pi, log2

import numpy

from PIL import Image   # poor mans OIIO
from OpenGL.GL import *

import viewport


VERTEX_GRASS_SHADER_SOURCE = """
#version 460 core

struct CurveData {
    vec3    A;  
    vec3    B;  
    vec3    C;  
};


// uniforms
layout(location = 0) uniform mat4 viewProjection;
layout(location = 1) uniform uint grassBlockSize;
layout(location = 2) uniform vec3 eye;

// ssbo
/*
    typedef  struct {
        uint  count;
        uint  primCount;
        uint  first;
        uint  baseInstance;
    } DrawArraysIndirectCommand;
*/
readonly layout(std430, binding = 0) buffer draw_arrays_commands_ { uint draw_arrays_commands[];};
readonly layout(std430, binding = 1) buffer curves_               { CurveData curves[];};

// attr
// layout(location = 0) in uint curveID;

// varying
layout(location = 0) out vec3 P;
layout(location = 1) out vec2 uv;
layout(location = 2) out vec3 N;


#define BEZINTERP(A, B, C, t) ((C + A - B*2)*t*t + (B*2 - A*2)*t + A)


void main() {

    uint vertexCount = draw_arrays_commands[4*gl_DrawID];
    CurveData curvePoints = curves[grassBlockSize*gl_DrawID + gl_InstanceID];

    float t = float(gl_VertexID >> 1) * 2.0 / float(vertexCount - 2);

    //  L----R
    //  |\   |
    //  | \  |
    //  |  \ |
    //  L----R
    float quadSide = float(gl_VertexID & 1);    // 0 = left, 1 = right

    vec3 left = normalize(cross(curvePoints.B-curvePoints.A, curvePoints.C-curvePoints.B));

    P = BEZINTERP(curvePoints.A, curvePoints.B, curvePoints.C, t) + left * (2 * quadSide - 1);
    uv = vec2(quadSide, t);
    N = normalize(mix(
         normalize(cross(curvePoints.B-curvePoints.A, left)),
         normalize(cross(curvePoints.C-curvePoints.B, left)),
        t
    ));

    // Grass texture has 4 blades equally split
    uv.x *= 0.25;
    uv.x += (float(gl_InstanceID & 3) * 0.25);
    uv.y = 1.0 - uv.y;  // Texture is curently upside down, this should be fixed
                        // before the texture upload

    gl_Position = viewProjection * vec4(P, 1.0);
}
"""

FRAGMENT_GRASS_SHADER_SOURCE = """
#version 460 core

layout(binding = 0) uniform sampler2D grassTexture;
layout(location = 2) uniform vec3 eye;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;
layout(location = 2) in vec3 N;


layout(location = 0) out vec4 outRgba;

void main() {

    vec4 col = texture(grassTexture, uv);
    float lod = textureQueryLod(grassTexture, uv).x + 1.0;
    col.w = float((lod * col.w) > 0.75);

    // Using discard seems to work better than setting the frag depth manually.
    #if 1
        if(col.w == 0) { discard; }
        float radiance = abs(dot(N, normalize(eye-P)));
        outRgba = vec4(col.xyz * radiance, 1.0);

    #else
        gl_FragDepth = gl_FragCoord.z + (1.0 - col.w);
        outRgba = vec4(col.xyz * abs(dot(N, normalize(eye-P))), col.w);
    #endif
}
"""

GRASS_INSTANCE_CULL = """
#version 460 core

layout(local_size_x=1) in;


layout(location = 0) uniform mat4 viewProjection;
layout(location = 1) uniform uint grassBlockSize;
layout(location = 2) uniform vec3 eye;

/*
    typedef  struct {
        uint  count;
        uint  primCount;
        uint  first;
        uint  baseInstance;
    } DrawArraysIndirectCommand;
*/
writeonly layout(std430, binding = 0) buffer drawArraysCommands_ { uint drawArraysCommands[];};

/*
    typedef  struct {
        vec4  mins, maxs;
    } BBox3d;
*/
readonly  layout(std430, binding = 2) buffer bboxs_ { vec4 bboxs[];};


void main() {
    
    uint idx = gl_GlobalInvocationID.x;

    vec4 bboxA = bboxs[2*idx];
    vec4 bboxB = bboxs[2*idx+1];

    mat4 bboxBlockA = viewProjection * mat4(
        bboxA,
        vec4(bboxA.x, bboxB.yzw),
        vec4(bboxA.xy, bboxB.zw),
        vec4(bboxA.x, bboxB.y, bboxA.zw)
    );
    bboxBlockA[0] /= bboxBlockA[0].w;
    bboxBlockA[1] /= bboxBlockA[1].w;
    bboxBlockA[2] /= bboxBlockA[2].w;
    bboxBlockA[3] /= bboxBlockA[3].w;

    mat4 bboxBlockB = viewProjection * mat4(
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

    vec3 midBox = (bboxA.xyz + bboxB.xyz) * 0.5;
    vec3 halfBoxDims = (bboxB.xyz - bboxA.xyz) * 0.5;

    vec3 q = abs(eye - midBox) - halfBoxDims;
    float distToBox = length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0);

    // TODO: Should probably screen resolution into account
    drawArraysCommands[4*idx + 0] = (4 + 2 * uint(4 * 1.0/(1.0 + distToBox*0.05))) * uint(!cull);;
    drawArraysCommands[4*idx + 1] = grassBlockSize * uint(!cull);
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

        self._buffers_ptr = None

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self._draw_grass_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=VERTEX_GRASS_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=FRAGMENT_GRASS_SHADER_SOURCE
        )
        self._cull_grass_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=GRASS_INSTANCE_CULL
        )

        self._vao_ptr = ctypes.c_int()
        self._buffers_ptr = (ctypes.c_int * 3)()

        glCreateBuffers(3, self._buffers_ptr)
        glCreateVertexArrays(1, self._vao_ptr)

        self._vao = self._vao_ptr.value
        self._draw_commands = self._buffers_ptr[0]
        self._curves = self._buffers_ptr[1]
        self._bboxs = self._buffers_ptr[2]

        def generate_grass(n, span, offset=(0, 0, 0)):
            X0 = ((numpy.random.random(n) * span) - span * 0.5) + offset[0]
            Y0 = numpy.zeros(n) + offset[1]
            Z0 = ((numpy.random.random(n) * span) - span * 0.5) + offset[2]
            
            X1 = (numpy.random.random(n) * 2 - 1) + X0
            Y1 = (numpy.random.random(n) * 5 + 5) + Y0
            Z1 = (numpy.random.random(n) * 2 - 1) + Z0
            
            X2 = (numpy.random.random(n) * 2 - 1) + X1
            Y2 = (numpy.random.random(n) * 3 + 1) + Y1
            Z2 = (numpy.random.random(n) * 2 - 1) + Z1
            
            padding = numpy.zeros(n)

            return numpy.column_stack((X0, Y0, Z0, padding, X1, Y1, Z1, padding, X2, Y2, Z2, padding))

        def generate_grass_blocks(blocksize, m, n, span):
            """Generate blocks of grass."""
            return numpy.array([
                generate_grass(blocksize, span, (x * span, 0, z * span))
                for x in range(m)
                for z in range(n)
            ], dtype=numpy.float32)

        def make_bbox(block):
            """Generate a BBOX for a block of grass blades."""
            min_values = block.min(axis=0)
            max_values = block.max(axis=0)
            minx = min_values[[0, 4, 8]].min()
            miny = min_values[[1, 5, 9]].min()
            minz = min_values[[2, 6, 10]].min()
            maxx = max_values[[0, 4, 8]].max()
            maxy = max_values[[1, 5, 9]].max()
            maxz = max_values[[2, 6, 10]].max()
            b = [minx, miny, minz, 1.0, maxx, maxy, maxz, 1.0]
            return b

        self._blocksize = 8192
        self._nblocksx = 16
        self._nblocksy = 16

        self._n_grass_draw_commands = self._nblocksx * self._nblocksy

        grass_blocks = generate_grass_blocks(
            self._blocksize,
            self._nblocksx,
            self._nblocksy,
            128
        )

        draw_commands = numpy.array([
            [
                4,                  # count
                self._blocksize,    # instanceCount
                0,                  # first
                i*self._blocksize,  # baseInstance
            ]
            for i in range(self._n_grass_draw_commands)
        ], dtype=numpy.uint32).tobytes()

        curves = grass_blocks.tobytes()

        bboxs = numpy.array([
            make_bbox(block) for block in grass_blocks
        ], dtype=numpy.float32).tobytes()


        glNamedBufferStorage(self._draw_commands, len(draw_commands), draw_commands, 0)
        glNamedBufferStorage(self._curves, len(curves), curves, 0)
        glNamedBufferStorage(self._bboxs, len(bboxs), bboxs, 0)

        # Load grass texture in the laziest way possible
        grass_image = Image.open("data/grass.png")
        grass_image_data = numpy.array(grass_image.getdata(), dtype=numpy.uint8)

        self._texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._texture_ptr)
        self._grass_tex = self._texture_ptr.value

        glTextureParameteri(self._grass_tex, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._grass_tex, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._grass_tex, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTextureParameteri(self._grass_tex, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTextureStorage2D(
            self._grass_tex,
            int(log2(grass_image.width)),
            GL_RGBA8,
            grass_image.width,
            grass_image.height
        )
        glTextureSubImage2D(
            self._grass_tex, 0, 0, 0,
            grass_image.width, grass_image.height,
            GL_RGBA, GL_UNSIGNED_BYTE,
            grass_image_data
        )

        glGenerateTextureMipmap(self._grass_tex)

        self.camera.look_at(numpy.array([0, 0, 0]), numpy.array([20, 5, 20]))
        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Cull shader
        glUseProgram(self._cull_grass_program)
        glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.view_projection.flatten())
        glUniform1ui(1, self._blocksize)
        glUniform3f(2, self.camera.eye[0], self.camera.eye[1], self.camera.eye[2])
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._draw_commands)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._curves)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._bboxs)

        glDispatchCompute(self._n_grass_draw_commands, 1, 1)
        glMemoryBarrier(GL_COMMAND_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT | GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)

        # Draw
        glUseProgram(self._draw_grass_program)
        glBindTextureUnit(0, self._grass_tex)

        glUniformMatrix4fv(0, 1, GL_FALSE, self.camera.view_projection.flatten())
        glUniform1ui(1, self._blocksize)
        glUniform3f(2, self.camera.eye[0], self.camera.eye[1], self.camera.eye[2])
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._draw_commands)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._curves)
        
        glBindVertexArray(self._vao)
        glBindBuffer(GL_DRAW_INDIRECT_BUFFER, self._draw_commands)

        glMultiDrawArraysIndirect(GL_TRIANGLE_STRIP, None, self._n_grass_draw_commands, 0)


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

