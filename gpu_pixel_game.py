
import os

import numpy

from OpenGL.GL import *
from PIL import Image

import viewport
import gpu_pixel_game_lib

_DEBUGGING = False

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_BVH_SHADER_DIR = os.path.join(_SHADER_DIR, "grid_based_bvh")

_DRAW_FULL_SCREEN_PATH = os.path.join(
    _SHADER_DIR, "draw_full_screen.vert"
)

_DRAW_BSP_MAP_DEBUG_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DRAW_BSP_MAP_DEBUG_FRAG
)

_GEN_MAP_ATLAS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GEN_MAP_ATLAS_COMP
)

_GEN_PATHFINDING_DIRECTIONS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GEN_PATHFINDING_DIRECTIONS_COMP
)

FINISH_MAP_GEN_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.FINISH_MAP_GEN_COMP
)

_DEBUG_VIS_PATHFINDING_DIRECTIONS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.DEBUG_VIS_PATHFINDING_DIRECTIONS_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_VIS_PATHFINDING_DIRECTIONS_FRAG
)

_RENDER_MAP_BACKGROUND_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.RENDER_MAP_BACKGROUND_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.RENDER_MAP_BACKGROUND_FRAG
)

_DEBUG_TEST_BACKGROUND_NORMALS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_TEST_BACKGROUND_NORMALS_FRAG
)

_GEN_MAP_LINES_COMP_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GEN_MAP_LINES_COMP
)

_GENERATE_BVH_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = os.path.join(_BVH_SHADER_DIR, "generate_bvh.comp")
)

_DEBUG_DRAW_LINES_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.DEBUG_DRAW_LINES_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_DRAW_LINES_FRAG
)


LEVEL_TILES_X = 128
LEVEL_TILES_Y = 128
MAX_LINES = 256
BVH_NUM_LEVELS = 3

class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_mouse = self._mouse
        self.window.on_keypress = self._keypress

        self._n = -1
        self._vis_pf_level = 0
        self._vis_pf_room = 0
        self._draw_lines = 1
        self._mouse_uv = (0.5, 0.5)

    def run(self):
        self.window.run()


    @staticmethod
    def _load_asset_png(png_path):
        asset_image = Image.open(png_path)
        asset_image_data = numpy.array(asset_image.getdata(), dtype=numpy.uint8)
        texture_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, texture_ptr)
        asset_tex = texture_ptr.value

        glTextureParameteri(asset_tex, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(asset_tex, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(asset_tex, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(asset_tex, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glTextureStorage2D(
            asset_tex,
            1,
            GL_RGBA8,
            asset_image.width,
            asset_image.height
        )
        glTextureSubImage2D(
            asset_tex, 0, 0, 0,
            asset_image.width,
            asset_image.height,
            GL_RGBA, GL_UNSIGNED_BYTE,
            asset_image_data
        )
        return asset_tex
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)

        buffer_ptr = (ctypes.c_int * 1)()
        with open(gpu_pixel_game_lib.ASSET_ATLAS_DATA, "rb") as in_fp:
            asset_atlas_data = in_fp.read()
        glCreateBuffers(1, buffer_ptr)
        self._asset_atlas_data = buffer_ptr[0]
        glNamedBufferStorage(self._asset_atlas_data, len(asset_atlas_data), asset_atlas_data, 0)

        self._asset_atlas_base = self._load_asset_png(
            gpu_pixel_game_lib.ASSET_ATLAS_BASE
        )
        self._asset_atlas_norm = self._load_asset_png(
            gpu_pixel_game_lib.ASSET_ATLAS_NORM
        )

        self._active_background_map_base = viewport.FramebufferTarget(GL_RGBA8, True)
        self._active_background_map_norm = viewport.FramebufferTarget(GL_RGBA8, True)
        self._active_background_map = viewport.Framebuffer(
            (self._active_background_map_base, self._active_background_map_norm),
            64 * 16,
            64 * 16
        )

        global_parameters = numpy.array(
            [
                0,          # cpuTime
                0,          # cpuAnimFrame
                0,          # cpuAnimTick
                0x12345678, # cpuRandom

                0,          # pipelineStage
                0,          # levelGenSeed
                0,          # currentLevel
                0,          # currentLevelMapStart
                0,          # currentLevelMapEnd
                0,          # numLines
                0,          # numLights
                # Padding
                0,
            ],
            dtype=numpy.uint32
        ).tobytes()

        self._buffers_ptr = (ctypes.c_int * 10)()
        glCreateBuffers(10, self._buffers_ptr)
        self._global_parameters = self._buffers_ptr[0]
        glNamedBufferStorage(self._global_parameters, len(global_parameters), global_parameters, 0)
        
        self._map_atlas_level_data = self._buffers_ptr[1]
        glNamedBufferStorage(self._map_atlas_level_data, (4 * 8 * (32 + 3)), None, 0)


        self._map_atlas_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._map_atlas_ptr)
        self._map_atlas = self._map_atlas_ptr.value

        glTextureParameteri(self._map_atlas, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._map_atlas, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTextureParameteri(self._map_atlas, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._map_atlas, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureStorage2D(
            self._map_atlas,
            1,
            GL_R32UI,
            LEVEL_TILES_X,
            LEVEL_TILES_Y
        )
        
        glClearTexImage(
            self._map_atlas,
            0,
            GL_RG_INTEGER ,
            GL_UNSIGNED_INT,
            numpy.array([0, 0], dtype=numpy.uint32).tobytes()
        )


        self._pathfinding_directions_ptr = ctypes.c_int()
        glCreateTextures(GL_TEXTURE_2D, 1, self._pathfinding_directions_ptr)
        self._pathfinding_directions = self._pathfinding_directions_ptr.value

        glTextureParameteri(self._pathfinding_directions, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTextureParameteri(self._pathfinding_directions, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTextureParameteri(self._pathfinding_directions, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self._pathfinding_directions, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTextureStorage2D(
            self._pathfinding_directions,
            1,
            GL_RG32UI,
            LEVEL_TILES_X * 2,
            LEVEL_TILES_Y
        )
        
        glClearTexImage(
            self._pathfinding_directions,
            0,
            GL_RG_INTEGER ,
            GL_UNSIGNED_INT,
            numpy.array([0, 0], dtype=numpy.uint32).tobytes()
        )
        
        def ubo_align_size(x):
            return x + (-x & 15)

        self._line_buffers_ptr = (ctypes.c_int * 3)()
        glCreateBuffers(3, self._line_buffers_ptr)

        self._lines_buffer = self._line_buffers_ptr[0]
        self._num_lines_buffer = self._line_buffers_ptr[1]
        glNamedBufferStorage(self._lines_buffer, MAX_LINES * 16, None, 0)
        glNamedBufferStorage(self._num_lines_buffer, ubo_align_size(4), None, 0)

        self._bvh_buffer = self._line_buffers_ptr[2]
        bvh_node_float4_size = 3
        bvh_grid_size = (1 << BVH_NUM_LEVELS)
        bvh_num_nodes = (bvh_grid_size * bvh_grid_size - 1)
        bvh_size_float4 = bvh_num_nodes * bvh_node_float4_size + MAX_LINES
        glNamedBufferStorage(self._bvh_buffer, bvh_size_float4 * 16, None, 0)

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(_GEN_MAP_ATLAS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_WRITE_ONLY, GL_R32UI)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._map_atlas_level_data)
        glDispatchCompute(1, 1, 8)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glUseProgram(_GEN_PATHFINDING_DIRECTIONS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
        glBindImageTexture(2, self._pathfinding_directions, 0, False, 0, GL_READ_WRITE, GL_RG32UI)
        glDispatchCompute(1, 1, 8 * 2)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(FINISH_MAP_GEN_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
        glBindImageTexture(2, self._pathfinding_directions, 0, False, 0, GL_READ_ONLY, GL_RG32UI)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._map_atlas_level_data)
        glDispatchCompute(1, 1, 8)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(_DRAW_BSP_MAP_DEBUG_PROGRAM.get(VS_OUTPUT_UV=0))
        glBindTextureUnit(0, self._map_atlas)
        # glBindTextureUnit(0, self._pathfinding_directions)
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_TRIANGLES, 0, 3)

        glUseProgram(_DEBUG_VIS_PATHFINDING_DIRECTIONS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
        glBindImageTexture(2, self._pathfinding_directions, 0, False, 0, GL_READ_ONLY, GL_RG32UI)
        glUniform2ui(0, self._vis_pf_level, self._vis_pf_room + 1)
        glDrawArrays(GL_TRIANGLES, 0, 64 * 64 * 6)

        with self._active_background_map.bind():
            glViewport(0, 0, 64 * 16, 64 * 16)
            glUseProgram(_RENDER_MAP_BACKGROUND_PROGRAM.one())
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._asset_atlas_data)
            glBindImageTexture(3, self._asset_atlas_base, 0, False, 0, GL_READ_ONLY, GL_RGBA8)
            glBindImageTexture(4, self._asset_atlas_norm, 0, False, 0, GL_READ_ONLY, GL_RGBA8)
            glDrawArrays(GL_TRIANGLES, 0, 64 * 64 * 6)
        glViewport(0, 0, wnd.width, wnd.height)

        # Generate visibility lines
        glUseProgram(_GEN_MAP_LINES_COMP_PROGRAM.get())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._num_lines_buffer)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._lines_buffer)
        glDispatchCompute(1, 1, 1)
        glMemoryBarrier(GL_UNIFORM_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)
 
        # Generate BVH
        glUseProgram(_GENERATE_BVH_PROGRAM.get(NUM_LINES_USE_UBO=1, NUM_LEVELS=BVH_NUM_LEVELS))
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._lines_buffer)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._bvh_buffer)
        glBindBufferBase(GL_UNIFORM_BUFFER, 2, self._num_lines_buffer)
        glDispatchCompute(1, 1, 1)

        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        glUseProgram(_DEBUG_TEST_BACKGROUND_NORMALS_PROGRAM.get(
            VS_OUTPUT_UV=0,
            ENABLE_SHADOW_CASTING=1
        ))
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindTextureUnit(1, self._active_background_map_base.texture)
        glBindTextureUnit(2, self._active_background_map_norm.texture)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._bvh_buffer)
        glUniform2f(0, self._mouse_uv[0], 1 - self._mouse_uv[1])
        glDrawArrays(GL_TRIANGLES, 0, 3)

        # Debug draw lines
        if self._draw_lines != 0:
            glUseProgram(_DEBUG_DRAW_LINES_PROGRAM.one())
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindBufferBase(GL_UNIFORM_BUFFER, 1, self._num_lines_buffer)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._lines_buffer)
            glDrawArrays(GL_LINES, 0, MAX_LINES * 2)


        wnd.redraw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):

        # CTRL-R
        if key == b'\x12':
            viewport.clear_compiled_shaders()
            print("RECOMPILIN SHADERS")
            wnd.redraw()
            return

        elif key == b'x':
            self._draw_lines ^= 1
            wnd.redraw()
            return

        elif key == b'l':
            self._vis_pf_level = (self._vis_pf_level + 1) & 7
            print("Level =", self._vis_pf_level)
        # ctrl+l
        elif key == b'\x0c':
            self._vis_pf_level = 0
            print("Level =", self._vis_pf_level)

        elif key == b'o':
            self._vis_pf_room = (self._vis_pf_room + 1) & 63
            print("Room =", self._vis_pf_room + 1)
        # ctrl+o
        elif key == b'\x0f':
            self._vis_pf_room = 0
            print("Room =", self._vis_pf_room + 1)

        elif key == b'c':
            self._n += 1

        glDeleteBuffers(1, self._buffers_ptr)
        glCreateBuffers(1, self._buffers_ptr)
        self._global_parameters = self._buffers_ptr[0]
        global_parameters = numpy.array(
            [
                0,          # cpuTime
                0,          # cpuAnimFrame
                0,          # cpuAnimTick
                self._n, # cpuRandom

                0,          # pipelineStage
                0,          # levelGenSeed
                self._vis_pf_level,          # currentLevel
                0,          # currentLevelMapStart
                0,          # currentLevelMapEnd
                0,          # numLines
                0,          # numLights
                # Padding
                0,
            ],
            dtype=numpy.uint32
        ).tobytes()
        glNamedBufferStorage(self._global_parameters, len(global_parameters), global_parameters, 0)


        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height
        self._mouse_uv = (
            self._mouse_uv[0] + deriv_u,
            self._mouse_uv[1] + deriv_v
        )
        wnd.redraw()

    def _mouse(self, wnd, button, state, x, y):
        self._mouse_uv = (x / wnd.width, y / wnd.height)
        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
