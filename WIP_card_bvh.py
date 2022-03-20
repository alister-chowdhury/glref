import viewport


from math import cos, sin, pi
import time

import numpy

from OpenGL.GL import *


import udim_vt_lib
import perf_overlay_lib
import card_bvh_lib


PREPASS_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;
layout(location = 0) out vec2 outUv;

void main() {
    outUv = uv;
    gl_Position = modelViewProjection * vec4(P, 1.0);
}
"""


PREPASS_FRAG_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec2 uv;

// We could half pack the derivs into ZW of the UVs as halfs directly
layout(location = 0) out vec2 outUv;
layout(location = 1) out vec4 outUvDerivs;

void main() {
    outUv = uv;
    // Could be abs'd and still work, GL doesnt have a unorm half format tho
    outUvDerivs = vec4(dFdx(uv), dFdy(uv));
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

        self._cards = None
        self.timer_overlay = perf_overlay_lib.TimerSamples256Overlay()


    def dirty_base(self):
        pass

    def run(self):
        self.window.run()

    def _init(self, wnd):

        self._cards = card_bvh_lib.CardBuffer.load_from_file(
            "data/card_bvh/scene0.card_data"
        )
        self._card_origins = None
        self._card_bboxs = None

        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glDisable(GL_CULL_FACE)


        self.camera.look_at(
            numpy.array([0, 3, 0]),
            numpy.array([0.83922848, 3.71858291, 0.52119542]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):
        # Draw stencil-depth HiZ
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        new_origin, new_bboxs = card_bvh_lib.generate_compact_cards(self._cards)

        if self._card_origins is not None:
            ptr = ctypes.c_int()
            ptr.value = self._card_origins
            glDeleteTextures(1, ptr)

        if self._card_bboxs is not None:
            ptr = ctypes.c_int()
            ptr.value = self._card_bboxs
            glDeleteTextures(1, ptr)

        self._card_origins = new_origin
        self._card_bboxs = new_bboxs

        # Does this work??!!
        # Be impressive if it does first try
        # Very very slow thou (atleast on python)
        bvh = card_bvh_lib.generate_bvh_python(
            self._cards
        )

        self._cards.debug_draw(self.camera.view_projection)
        self._cards.debug_compact_bbox(self._card_bboxs, self.camera.view_projection)
        self.timer_overlay.update(wnd.width, wnd.height)

        wnd.redraw()        

    def _resize(self, wnd, width, height):
        self.dirty_base()
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)


    def _keypress(self, wnd, key, x, y):
        # Move the camera
        shift = key.isupper()
        key = key.lower()
        move_amount = 0.1 + 0.9 * shift

        if key == b'w':
            self.camera.move_local(numpy.array([0, 0, move_amount]))
        elif key == b's':
            self.camera.move_local(numpy.array([0, 0, -move_amount]))

        elif key == b'a':
            self.camera.move_local(numpy.array([move_amount, 0, 0]))
        elif key == b'd':
            self.camera.move_local(numpy.array([-move_amount, 0, 0]))

        elif key == b'q':
            self.camera.move_local(numpy.array([0, move_amount, 0]))
        elif key == b'e':
            self.camera.move_local(numpy.array([0, -move_amount, 0]))

        elif key == b'.':
            self._text_size += 0.5
        elif key == b',':
            self._text_size -= 0.5

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # No redraw
        else:
            return

        self.dirty_base()
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
        else:
            N = numpy.matrix([
                [1, 0, 0],
                [0, cos_v, -sin_v],
                [0, sin_v, cos_v],
            ])
        N = ortho * N * ortho.I
        M *= N

        self.camera.append_3x3_transform(M)
        self.dirty_base()
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()




