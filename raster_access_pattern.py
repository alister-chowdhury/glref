import numpy

from OpenGL.GL import *

import viewport


VERTEX_SHADER_SOURCE = """
#version 460 core

void main() {

    vec2 uv = vec2(
        float(gl_VertexID) - 0.5,
        float(gl_VertexID & 1) * 2.0
    );
    gl_Position = vec4(
        2.0 * uv - 1.0,
        0,
        1
    );
}
"""

FRAGMENT_SHADER_SOURCE = """
#version 460 core


layout(std430, binding = 0) buffer incrementor_ { uint incrementor;};
layout(location = 1) uniform float invImageArea;

layout(location = 0) out vec4 outRgba;


void main()
{
    uint v = atomicAdd(incrementor, 1);

    if(invImageArea != 0.0)
    {
        outRgba = vec4(vec3(float(v) * invImageArea), 1.0);
    }
    else
    {
        outRgba = vec4(
            float(v & 0xff) / 255.0,
            float((v >> 8) & 0xff) / 255.0,
            float((v >> 16) & 0xff) / 255.0,
            1.0
        );
    }

}
"""

CLEAR_INCREMENTOR = """
#version 460 core

layout(local_size_x=1) in;


layout(std430, binding = 0) buffer incrementor_ { uint incrementor;};

void main()
{
    incrementor = 0;
}

"""

class Renderer(object):

    def __init__(self):

        self.window = viewport.Window()

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_keypress = self._keypress

        self.linear_mode = False

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self.clear_incrementor_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=CLEAR_INCREMENTOR
        )
        self.draw_screen_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=FRAGMENT_SHADER_SOURCE,
        )

        self._vao_ptr = ctypes.c_int()
        glCreateVertexArrays(1, self._vao_ptr)
        self._dummy_vao = self._vao_ptr.value

        self._incrementor_ptr = ctypes.c_int();
        glCreateBuffers(1, self._incrementor_ptr)
        self._incrementor = self._incrementor_ptr.value

        zero = numpy.array([0], dtype=numpy.uint32).tobytes()
        glNamedBufferStorage(self._incrementor, len(zero), zero, 0)

        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.clear_incrementor_program)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._incrementor)
        glDispatchCompute(1, 1, 1)
        glMemoryBarrier(GL_COMMAND_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(self.draw_screen_program)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._incrementor)
        if self.linear_mode:
            glUniform1f(1, 1.0 / (wnd.width * wnd.height))
        else:
            glUniform1f(1, 0.0)
        glBindVertexArray(self._dummy_vao)
        glDrawArrays(GL_TRIANGLES, 0, 3)

    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):
        # Switch mode
        if key == b'm':
            self.linear_mode = not self.linear_mode
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()
