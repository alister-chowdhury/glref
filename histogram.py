import numpy
from math import cos, sin, pi

from OpenGL.GL import *

import viewport


VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;

layout(location = 0) out vec3 outP;
layout(location = 1) out vec2 outUv;

void main()
{
    vec4 worldP = model * vec4(P, 1.0);
    outP = worldP.xyz / worldP.w;
    outUv = uv;
    gl_Position = modelViewProjection * vec4(P, 1.0);
}
"""

FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 2) uniform uint displayMode;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;

layout(location = 0) out vec4 outRgba;


void main() {
    switch(displayMode)
    {
        case 0: outRgba = vec4(P, 1.0); break;
        case 1: outRgba = vec4(uv, 0.0, 1.0); break;
    }
}
"""

CLEAR_HISTOGRAM_SOURCE = """
#version 460 core

layout(local_size_x=16, local_size_y=16) in;
layout(std430, binding = 0) buffer histogramGlobal_ { uint histogramGlobal[];};

void main()
{
    histogramGlobal[gl_LocalInvocationIndex] = 0;
}
"""

HISTOGRAM_SOURCE = """
#version 460 core

layout(local_size_x=16, local_size_y=16) in;
layout(std430, binding = 0) buffer histogramGlobal_ { uint histogramGlobal[];};
readonly layout(binding = 1, rgba8ui)  uniform uimage2D lumaReference;

layout(location = 0) uniform uvec2 imageDimensions;

shared uint histogramLocal[256];


void main()
{
    histogramLocal[gl_LocalInvocationIndex] = 0;
    groupMemoryBarrier();

    // Process 4 pixels at a time, meaning each group of 16x16 will process blocks of 64x64
    // storing the result in a locally shared table.
    uvec2 gid = gl_GlobalInvocationID.xy * 4;
    for(uint u=0; u<4; ++u)
    {
        for(uint v=0; v<4; ++v)
        {
            uvec2 st = gid + uvec2(u, v);
            if(st.x < imageDimensions.x && st.y < imageDimensions.y)
            {
                const float Y = clamp(
                    dot(vec3(0.2126, 0.7152, 0.0722), vec3(imageLoad(lumaReference, ivec2(st)).xyz)),
                    0.0,
                    255.0
                );
                atomicAdd(histogramLocal[uint(Y)], 1);
            }
            groupMemoryBarrier();
        }
    }

    // Writeback to the global table
    barrier();
    atomicAdd(histogramGlobal[gl_LocalInvocationIndex], histogramLocal[gl_LocalInvocationIndex]);
}

"""

DRAW_HISTOGRAM_VERTEX = """
#version 460 core

layout(location = 0) out vec2 uv;
flat layout(location = 1) out float normFactor;

layout(std430, binding = 0) buffer histogramGlobal_ { uint histogramGlobal[];};

void main()
{

    // This is bad and wrong
    uint maxValue = 0;
    for(uint i=0; i<256; ++i)
    {
        maxValue = max(maxValue, histogramGlobal[i]);
    }
    normFactor = 1.0 / (0.25 * float(maxValue));

    uv = vec2(
        float(gl_VertexID % 2),
        float(gl_VertexID / 2)
    );

    uv.y *= 0.1;  // take up only 1th of the screen

    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}
"""

DRAW_HISTOGRAM_FRAG = """
#version 460 core

layout(location = 0) in vec2 uv;
flat layout(location = 1) in float normFactor;

layout(std430, binding = 0) buffer histogramGlobal_ { uint histogramGlobal[];};

layout(location = 0) out vec4 outRgba;

void main()
{
    uint idx = clamp(uint(256 * uv.x), uint(0), uint(255));
    float blackbarMask = float(uv.y < 0.095);

    float col = float(histogramGlobal[idx]) * normFactor;
    outRgba = vec4(vec3(col * blackbarMask), 1.0);
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

        # Default to drawing position
        self.display_mode = 0

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self.draw_screen_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=FRAGMENT_SHADER_SOURCE,
        )
        self.clear_histogram_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=CLEAR_HISTOGRAM_SOURCE
        )
        self.histogram_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=HISTOGRAM_SOURCE
        )
        self.draw_histogram_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_HISTOGRAM_VERTEX,
            GL_FRAGMENT_SHADER=DRAW_HISTOGRAM_FRAG,
        )

        self.plane = viewport.StaticGeometry(
            (3, 2),
            viewport.PLANE_INDICES,
            viewport.PUV_PLANE_VERTICES,
        )

        self.cube = viewport.StaticGeometry(
            (3, 2),
            viewport.CUBE_INDICES,
            viewport.PUV_CUBE_VERTICES,
        )

        self._cube_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1.5, 0, 1],
        ], dtype=numpy.float32)

        self._plane_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0.5],
        ], dtype=numpy.float32)

        self._histogram_ptr = ctypes.c_int()
        glCreateBuffers(1, self._histogram_ptr)
        self._histogram = self._histogram_ptr.value

        glNamedBufferStorage(self._histogram, 256*4, None, GL_MAP_READ_BIT)

        self._framebuffer_col = viewport.FramebufferTarget(GL_RGBA8, True)
        self._framebuffer_depth = viewport.FramebufferTarget(GL_DEPTH_COMPONENT, True)
        self._framebuffer = viewport.Framebuffer(
            (self._framebuffer_col, self._framebuffer_depth),
            wnd.width,
            wnd.height
        )

        self.camera.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )
        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):

        # Clear existing histogram
        glUseProgram(self.clear_histogram_program)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._histogram)
        glDispatchCompute(1, 1, 1)

        # Draw stuff
        with self._framebuffer.bind():
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glEnable(GL_DEPTH_TEST)

            glUseProgram(self.draw_screen_program)
            glUniform1ui(2, self.display_mode)

            glUniformMatrix4fv(0, 1, GL_FALSE, self._cube_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._cube_model * self.camera.view_projection).flatten())
            self.cube.draw()

            glUniformMatrix4fv(0, 1, GL_FALSE, self._plane_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._plane_model * self.camera.view_projection).flatten())
            self.plane.draw()

        # Generate histogram
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
        glUseProgram(self.histogram_program)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._histogram)
        glBindImageTexture(1, self._framebuffer_col.texture, 0, False, 0, GL_READ_ONLY, GL_RGBA8UI)
        glUniform2ui(0, wnd.width, wnd.height)
        glDispatchCompute((wnd.width + 63)//64, (wnd.height + 63)//64, 1)

        # Draw framebuffer to back
        self._framebuffer.blit_to_back(wnd.width, wnd.height)

        # # Read the histogram data
        # glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT)
        # histogram_data = (c_int * 256)()
        # glGetNamedBufferSubData(self._histogram, 0, 4*256, histogram_data)
        # print([x for x in histogram_data])

        # Draw the historgram at the the bottom
        # (make use of whatever VAO was last bound)
        glDisable(GL_DEPTH_TEST)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
        glUseProgram(self.draw_histogram_program)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._histogram)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)
        self._framebuffer.resize(width, height)
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
        elif key == b'u':
            self.display_mode = 1

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
