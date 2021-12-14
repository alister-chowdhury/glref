import viewport


from math import cos, sin, pi
import time

import numpy

from OpenGL.GL import *


import udim_vt_lib
import perf_overlay_lib



PREPASS_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;
layout(location = 1) in vec2 uv;
layout(location = 0) out vec2 outUv;

void main() {
    outUv = uv * 2;
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

        self.main_geom = None
        
        self.udim_offset = None
        self.udim_info_start = None
        self.udim_info = None
        self.dirty_base_update = True
        self.timer_overlay = perf_overlay_lib.TimerSamples256Overlay()


    def dirty_base(self):
        self.dirty_base_update = True

    def run(self):
        self.window.run()

    def _init(self, wnd):
        glClearColor(0.5, 0.5, 0.5, 0.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glDisable(GL_CULL_FACE)


        self.main_geom = viewport.load_obj(
            # "data/cubeWithNormals.obj",
            "data/armadillo.obj",
            (
                viewport.ObjGeomAttr.P,
                viewport.ObjGeomAttr.UV,
            )
        )

        self._main_geom_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1.5, 0, 1],
        ], dtype=numpy.float32)


        self._prepass_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=PREPASS_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=PREPASS_FRAG_SHADER_SOURCE,
        )

        self._apply_vt_program = viewport.generate_shader_program(
            GL_COMPUTE_SHADER=udim_vt_lib.APPLY_VT_TEXTURES_CS
        )

        self._framebuffer_depth = viewport.FramebufferTarget(
            GL_DEPTH32F_STENCIL8,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )

        self._framebuffer_col = viewport.FramebufferTarget(
            GL_RGBA8,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )

        self._fb_uv = viewport.FramebufferTarget(
            GL_RG32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )

        self._fb_uv_derivs = viewport.FramebufferTarget(
            GL_RGBA32F,
            True,
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
            }
        )

        self._prepass_framebuffer = viewport.Framebuffer(
            (
                self._framebuffer_depth,
                self._fb_uv,
                self._fb_uv_derivs,
            ),
            wnd.width,
            wnd.height
        )

        self._scene_col_fb = viewport.Framebuffer(
            (
                viewport.ProxyFramebufferTarget(self._framebuffer_depth),
                self._framebuffer_col,
            ),
            wnd.width,
            wnd.height,
        )

        udim_ind_data = udim_vt_lib.UdimIndirectionBuilder([
            udim_vt_lib.UdimEntry(
                (0, 0),
                udim_vt_lib.Image(r"C:\Users\thoth\Desktop\im0.png")
            ),
            udim_vt_lib.UdimEntry(
                (1, 0),
                udim_vt_lib.Image(r"C:\Users\thoth\Desktop\im1.png")
            ),
            udim_vt_lib.UdimEntry(
                (0, 1),
                udim_vt_lib.Image(r"C:\Users\thoth\Desktop\im2.png")
            ),
            udim_vt_lib.UdimEntry(
                (1, 1),
                udim_vt_lib.Image(r"C:\Users\thoth\Desktop\mickey.png")
            ),
            udim_vt_lib.UdimEntry(
                (10, 100),
                udim_vt_lib.Image(r"C:\Users\thoth\Desktop\im2.png")
            ),
        ])

        self.udim_offset = (
            udim_ind_data.udim_offset[0],
            udim_ind_data.udim_offset[1],
            udim_ind_data.udim_info_start.shape[1],
            udim_ind_data.udim_info_start.shape[0]
        )

        self._buffers_ptr = (ctypes.c_int * 1)()
        glCreateBuffers(1, self._buffers_ptr)

        self.udim_info = self._buffers_ptr[0]
        udim_info_raw = udim_ind_data.udim_info.tobytes()
        glNamedBufferStorage(self.udim_info, len(udim_info_raw), udim_info_raw, 0)

        self._udim_info_start_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._udim_info_start_ptr)
        self._udim_info_start = self._udim_info_start_ptr.value
        glTextureParameteri(self._udim_info_start, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._udim_info_start, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._udim_info_start, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
        glTextureParameteri(self._udim_info_start, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureStorage2D(
            self._udim_info_start,
            1,
            GL_R32UI,
            udim_ind_data.udim_info_start.shape[1],
            udim_ind_data.udim_info_start.shape[0]
        )
        glTextureSubImage2D(
            self._udim_info_start,
            0, 0, 0,
            udim_ind_data.udim_info_start.shape[1],
            udim_ind_data.udim_info_start.shape[0],
            GL_RED_INTEGER,
            GL_UNSIGNED_INT,
            udim_ind_data.udim_info_start.tobytes()
        )

        self._vt_indirection_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D_ARRAY, 1, self._vt_indirection_ptr)
        self._vt_indirection = self._vt_indirection_ptr.value
        glTextureParameteri(self._vt_indirection, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._vt_indirection, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._vt_indirection, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
        glTextureParameteri(self._vt_indirection, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureStorage3D(
            self._vt_indirection,
            1,
            GL_R16UI,
            udim_ind_data.mip_indirection_size[0],
            udim_ind_data.mip_indirection_size[1],
            udim_ind_data.mip_indirection_size[2]
        )

        clear_vt_ptr = ctypes.c_long()
        clear_vt_ptr.value = ~0
        glClearTexImage(self._vt_indirection, 0, GL_RED_INTEGER, GL_UNSIGNED_SHORT, clear_vt_ptr)


        self._virtual_texture_dim = (8192, 8192, 2)
        self._inv_virtual_texture_size = (1/8192, 1/8192)

        self._virtual_texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D_ARRAY, 1, self._virtual_texture_ptr)
        self._virtual_texture = self._virtual_texture_ptr.value
        glTextureParameteri(self._virtual_texture, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._virtual_texture, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self._virtual_texture, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTextureParameteri(self._virtual_texture, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTextureStorage3D(
            self._virtual_texture,
            1,
            GL_RGBA8,
            self._virtual_texture_dim[0],
            self._virtual_texture_dim[1],
            self._virtual_texture_dim[2]
        )
        

        self._max_feedback_values = 1024 * 1024
        self._feedback_buffers_ptr = (ctypes.c_int * 2)()
        glCreateBuffers(2, self._feedback_buffers_ptr)
        self._feedback_counter = self._feedback_buffers_ptr[0]
        self._feedback_storage = self._feedback_buffers_ptr[1]
        glNamedBufferStorage(self._feedback_counter, 4, None, 0)
        glNamedBufferStorage(
            self._feedback_storage,
            self._max_feedback_values * 8, # u64 per result
            None,
            0
        )

        self.camera.look_at(
            numpy.array([0, 3, 0]),
            numpy.array([0.83922848, 3.71858291, 0.52119542]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):

        # Turn this on to make things slow
        if False:
            if not hasattr(self, "COUNTER_TMP"):
                self.COUNTER_TMP = 0
            if not hasattr(self, "UNIQUE_TMP"):
                self.UNIQUE_TMP = 0

            counter_ptr = ctypes.c_int()
            glGetNamedBufferSubData(
                self._feedback_counter,
                0,
                4,
                counter_ptr
            )
            # The < 1024 * 1024 thing shouldnt be needed
            if counter_ptr.value > 0:
                count = min(1024*1024, counter_ptr.value)
                tiles_data_ptr = (ctypes.c_uint64 * count)()
                glGetNamedBufferSubData(
                    self._feedback_storage,
                    0,
                    8 * count,
                    tiles_data_ptr
                )
                uniq_tiles = set(tiles_data_ptr)
                if self.UNIQUE_TMP != len(uniq_tiles):
                    print("uniq: ", len(uniq_tiles))
                    self.UNIQUE_TMP = len(uniq_tiles)

            if counter_ptr.value > self.COUNTER_TMP:
                self.COUNTER_TMP = counter_ptr.value
                print(self.COUNTER_TMP)


        # Draw stencil-depth HiZ
        if self.dirty_base_update:
            with self._prepass_framebuffer.bind():
                glStencilFunc(GL_ALWAYS, 1, 0xFF)
                glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
                glStencilMask(0xFF)
                glDepthFunc(GL_LEQUAL)
                glClear(GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
                glUseProgram(self._prepass_program)
                glUniformMatrix4fv(0, 1, GL_FALSE, (self._main_geom_model * self.camera.view_projection).flatten())
                self.main_geom.draw()
            self.dirty_base_update = False

        # Clear feedback stuff
        clear_ptr = ctypes.c_int()
        clear_ptr.value = 0
        glClearNamedBufferData(
            self._feedback_counter,
            GL_R32UI,
            GL_RED_INTEGER,
            GL_UNSIGNED_INT,
            clear_ptr
        )

        # We don't need to clear the feedback storage, as we use the count
        # to determine how much to read
        
        # glMemoryBarrier(GL_FRAMEBUFFER_BARRIER_BIT | GL_BUFFER_UPDATE_BARRIER_BIT)
        glMemoryBarrier(GL_ALL_BARRIER_BITS)


        glUseProgram(self._apply_vt_program)
        glBindImageTexture(
            0,
            self._framebuffer_col.texture,
            0,
            0,
            0,
            GL_WRITE_ONLY,
            GL_RGBA8
        )
        glBindImageTexture(
            1,
            self._fb_uv.texture,
            0,
            0,
            0,
            GL_READ_ONLY,
            GL_RG32F
        )
        glBindImageTexture(
            2,
            self._fb_uv_derivs.texture,
            0,
            0,
            0,
            GL_READ_ONLY,
            GL_RGBA32F
        )
        glBindTextureUnit(3, self._framebuffer_depth.texture)

        glBindImageTexture(
            4,
            self._udim_info_start,
            0,
            0,
            0,
            GL_READ_ONLY,
            GL_R32UI
        )

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 5, self.udim_info)
        glBindTextureUnit(6, self._vt_indirection)
        glBindTextureUnit(7, self._virtual_texture)

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 8, self._feedback_counter)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 9, self._feedback_storage)

        glUniform4i(
            0,
            self.udim_offset[0],
            self.udim_offset[1],
            self.udim_offset[2],
            self.udim_offset[3]
        )

        glUniform2i(
            1,
            wnd.width,
            wnd.height,
        )

        glUniform2f(
            2,
            self._inv_virtual_texture_size[0],
            self._inv_virtual_texture_size[1],
        )

        glDispatchCompute((wnd.width + 7)//8, (wnd.height + 7)//8, 1)
        # glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
        glMemoryBarrier(GL_ALL_BARRIER_BITS)


        self._scene_col_fb.blit_to_back(
            wnd.width,
            wnd.height,
            GL_COLOR_BUFFER_BIT,
            GL_NEAREST
        )

        self.timer_overlay.update(wnd.width, wnd.height)

        wnd.redraw()        

    def _resize(self, wnd, width, height):
        self._prepass_framebuffer.resize(width, height)
        self._scene_col_fb.resize(width, height)
        # self._draw_framebuffer.resize(width, height)
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




