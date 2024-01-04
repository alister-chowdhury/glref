
import os

import numpy

from OpenGL.GL import *
from ctypes import c_void_p
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

_VIS_CLEAR_HISTORY_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.VIS_CLEAR_HISTORY_FRAG
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

_GEN_DISTANCE_FIELD_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.GEN_DISTANCE_FIELD_FRAG
)

_GEN_MAP_LINES_COMP_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GEN_MAP_LINES_COMP
)

_GENERATE_BVH_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = os.path.join(_BVH_SHADER_DIR, "generate_bvh.comp")
)

_GEN_DIRECT_LIGHTING_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.GEN_DIRECT_LIGHTING_FRAG
)

_FILTER_DIRECT_LIGHTING_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.FILTER_DIRECT_LIGHTING_FRAG
)

_DEBUG_DRAW_LINES_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.DEBUG_DRAW_LINES_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_DRAW_LINES_FRAG
)

_DEBUG_SET_PLAYER_POS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.DEBUG_SET_PLAYER_POS_COMP
)

_VIS_GENERATE_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.VIS_GENERATE_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.VIS_GENERATE_FRAG
)

_VIS_GENERATE_CLEAR_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.VIS_GENERATE_CLEAR_FRAG
)

_VIS_FILTER_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.VIS_FILTER_FRAG
)

_VIS_UPDATE_HISTORY_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.VIS_UPDATE_HISTORY_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.VIS_UPDATE_HISTORY_FRAG
)

_DEBUG_TEST_BACKGROUND_NORMALS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_TEST_BACKGROUND_NORMALS_FRAG
)

_DEBUG_TEST_DF_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_TEST_DF_FRAG
)


LEVEL_TILES_X = 128
LEVEL_TILES_Y = 128

VIS_BUFFER_TILE_SIZE = 8

VIS_HISTORY_X = LEVEL_TILES_X * VIS_BUFFER_TILE_SIZE
VIS_HISTORY_Y = LEVEL_TILES_Y * VIS_BUFFER_TILE_SIZE

ACTIVE_NUM_TILES = 64
BACKGROUND_TILE_SIZE = 16
DF_TILE_SIZE = 4
DIRECT_LIGHTING_TILE_SIZE = 8

ACTIVE_BACKGROUND_SIZE = ACTIVE_NUM_TILES * BACKGROUND_TILE_SIZE
ACTIVE_DIRECT_LIGHTING_SIZE = ACTIVE_NUM_TILES * DIRECT_LIGHTING_TILE_SIZE
ACTIVE_VIS_SIZE = ACTIVE_NUM_TILES * VIS_BUFFER_TILE_SIZE
ACTIVE_DF_SIZE = ACTIVE_NUM_TILES * DF_TILE_SIZE

MAX_LINES = 512
BVH_NUM_LEVELS = 3

VIS_DISPATCH_OFFSET = 0

        
def ubo_align_size(x):
    return x + (-x & 15)


class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(1024, 1024)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_mouse = self._mouse
        self.window.on_keypress = self._keypress

        self._dirty_init_levels = True
        self._dirty_load_level = True

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

        lininterp_texture_settings = {
            GL_TEXTURE_WRAP_S: GL_REPEAT,
            GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
            GL_TEXTURE_MIN_FILTER: GL_LINEAR,
            GL_TEXTURE_MAG_FILTER: GL_LINEAR
        }
        
        self._vis_history = viewport.FramebufferTarget(
            GL_R8,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._vis_history_fb = viewport.Framebuffer(
            (self._vis_history,),
            VIS_HISTORY_X,
            VIS_HISTORY_Y
        )

        self._active_background_map_base = viewport.FramebufferTarget(GL_RGBA8, True)
        self._active_background_map_norm = viewport.FramebufferTarget(GL_RGBA8, True)
        self._active_background_map = viewport.Framebuffer(
            (self._active_background_map_base, self._active_background_map_norm),
            ACTIVE_BACKGROUND_SIZE,
            ACTIVE_BACKGROUND_SIZE
        )


        self._df_bg_map = viewport.FramebufferTarget(
            GL_R16F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._df_bg_map_fb = viewport.Framebuffer(
            (
                self._df_bg_map,
            ),
            ACTIVE_DF_SIZE,
            ACTIVE_DF_SIZE
        )


        self._direct_lighting_bg_map_v0 = viewport.FramebufferTarget(
            GL_R11F_G11F_B10F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._direct_lighting_bg_map_v1 = viewport.FramebufferTarget(
            GL_RGBA16F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._direct_lighting_bg_map_v2 = viewport.FramebufferTarget(
            GL_RG16F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._direct_lighting_bg_map = viewport.Framebuffer(
            (
                self._direct_lighting_bg_map_v0,
                self._direct_lighting_bg_map_v1,
                self._direct_lighting_bg_map_v2,
            ),
            ACTIVE_DIRECT_LIGHTING_SIZE,
            ACTIVE_DIRECT_LIGHTING_SIZE
        )

        self._filt_direct_lighting_bg_map_v0 = viewport.FramebufferTarget(
            GL_R11F_G11F_B10F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._filt_direct_lighting_bg_map_v1 = viewport.FramebufferTarget(
            GL_RGBA16F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._filt_direct_lighting_bg_map_v2 = viewport.FramebufferTarget(
            GL_RG16F,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._filt_direct_lighting_bg_map = viewport.Framebuffer(
            (
                self._filt_direct_lighting_bg_map_v0,
                self._filt_direct_lighting_bg_map_v1,
                self._filt_direct_lighting_bg_map_v2,
            ),
            ACTIVE_DIRECT_LIGHTING_SIZE,
            ACTIVE_DIRECT_LIGHTING_SIZE
        )

        self._active_vis = viewport.FramebufferTarget(
            GL_R8,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._active_vis_fb = viewport.Framebuffer(
            (self._active_vis,),
            ACTIVE_VIS_SIZE,
            ACTIVE_VIS_SIZE
        )

        self._filt_active_vis = viewport.FramebufferTarget(
            GL_R8,
            True,
            custom_texture_settings=lininterp_texture_settings
        )
        self._filt_active_vis_stencil = viewport.FramebufferTarget(
            GL_STENCIL_INDEX8,
            False
        )
        self._filt_active_vis_fb = viewport.Framebuffer(
            (self._filt_active_vis, self._filt_active_vis_stencil),
            ACTIVE_VIS_SIZE,
            ACTIVE_VIS_SIZE
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

        # gonna need to deal with this better
        indirection_table = numpy.array(
            [
                # vis history
                0, 1, 0, 0
            ],
            dtype=numpy.uint32
        ).tobytes()

        self._indirection_table = self._buffers_ptr[2]
        glNamedBufferStorage(self._indirection_table, len(indirection_table), indirection_table, 0)

        self._player_pos = self._buffers_ptr[3]
        glNamedBufferStorage(self._player_pos, ubo_align_size(4*2), None, 0)

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

        if self._dirty_init_levels:
            self._dirty_init_levels = False
            self._dirty_load_level = True
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

            with self._vis_history_fb.bind():
                glViewport(0, 0, VIS_HISTORY_X, VIS_HISTORY_Y)
                glUseProgram(_VIS_CLEAR_HISTORY_PROGRAM.get())
                glBindVertexArray(viewport.get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 3)

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
            glDrawArrays(GL_TRIANGLES, 0, ACTIVE_NUM_TILES * ACTIVE_NUM_TILES * 6)


        if self._dirty_load_level:
            self._dirty_load_level = False
            # Generate visibility lines
            glUseProgram(_GEN_MAP_LINES_COMP_PROGRAM.get(OUT_VIS_DISPATCH_ADDR=VIS_DISPATCH_OFFSET))
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._num_lines_buffer)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._lines_buffer)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 4, self._indirection_table)
            glDispatchCompute(1, 1, 1)
            glMemoryBarrier(GL_UNIFORM_BARRIER_BIT | GL_SHADER_STORAGE_BARRIER_BIT)
     
            # Generate BVH
            glUseProgram(_GENERATE_BVH_PROGRAM.get(NUM_LINES_USE_UBO=1, NUM_LEVELS=BVH_NUM_LEVELS))
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._lines_buffer)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._bvh_buffer)
            glBindBufferBase(GL_UNIFORM_BUFFER, 2, self._num_lines_buffer)
            glDispatchCompute(1, 1, 1)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

            with self._df_bg_map_fb.bind():
                glViewport(0, 0, ACTIVE_DF_SIZE, ACTIVE_DF_SIZE)
                glUseProgram(_GEN_DISTANCE_FIELD_PROGRAM.get(VS_OUTPUT_UV=0))
                glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._bvh_buffer)
                glBindVertexArray(viewport.get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 3)

            with self._filt_direct_lighting_bg_map.bind():
                glViewport(0, 0, ACTIVE_DIRECT_LIGHTING_SIZE, ACTIVE_DIRECT_LIGHTING_SIZE)
                glUseProgram(_GEN_DIRECT_LIGHTING_PROGRAM.get(VS_OUTPUT_UV=0))
                glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
                glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._map_atlas_level_data)
                glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._bvh_buffer)
                glBindVertexArray(viewport.get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 3)

            with self._direct_lighting_bg_map.bind():
                glViewport(0, 0, ACTIVE_DIRECT_LIGHTING_SIZE, ACTIVE_DIRECT_LIGHTING_SIZE)
                glUseProgram(_FILTER_DIRECT_LIGHTING_PROGRAM.get(VS_OUTPUT_UV=0))
                glBindTextureUnit(0, self._filt_direct_lighting_bg_map_v0.texture)
                glBindTextureUnit(1, self._filt_direct_lighting_bg_map_v1.texture)
                glBindTextureUnit(2, self._filt_direct_lighting_bg_map_v2.texture)
                glBindVertexArray(viewport.get_dummy_vao())
                glDrawArrays(GL_TRIANGLES, 0, 3)

            with self._active_background_map.bind():
                glViewport(0, 0, ACTIVE_BACKGROUND_SIZE, ACTIVE_BACKGROUND_SIZE)
                glUseProgram(_RENDER_MAP_BACKGROUND_PROGRAM.one())
                glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
                glBindImageTexture(1, self._map_atlas, 0, False, 0, GL_READ_ONLY, GL_R32UI)
                glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._asset_atlas_data)
                glBindImageTexture(3, self._asset_atlas_base, 0, False, 0, GL_READ_ONLY, GL_RGBA8)
                glBindImageTexture(4, self._asset_atlas_norm, 0, False, 0, GL_READ_ONLY, GL_RGBA8)
                glBindTextureUnit(5, self._df_bg_map.texture)
                glDrawArrays(GL_TRIANGLES, 0, ACTIVE_NUM_TILES * ACTIVE_NUM_TILES * 6)


        # PLAYING STUFF

        glUseProgram(_DEBUG_SET_PLAYER_POS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._player_pos)
        glUniform2f(0, self._mouse_uv[0], 1 - self._mouse_uv[1])
        glDispatchCompute(1, 1, 1)

        # Initial visibility
        glViewport(0, 0, ACTIVE_VIS_SIZE, ACTIVE_VIS_SIZE)
        with self._filt_active_vis_fb.bind():
            glEnable(GL_STENCIL_TEST)
            glClear(GL_STENCIL_BUFFER_BIT)
            glStencilMask(0xFF)

            glStencilOp(GL_KEEP, GL_KEEP, GL_INCR)
            glStencilFunc(GL_EQUAL, 0, 0xFF)
            glUseProgram(_VIS_GENERATE_PROGRAM.one())
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._lines_buffer)
            glBindBufferBase(GL_UNIFORM_BUFFER, 1, self._player_pos)
            glBindBuffer(GL_DRAW_INDIRECT_BUFFER, self._indirection_table)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArraysIndirect(GL_TRIANGLES, c_void_p(VIS_DISPATCH_OFFSET * 4))

            glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
            glUseProgram(_VIS_GENERATE_CLEAR_PROGRAM.one())
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

            glDisable(GL_STENCIL_TEST)

        # Filtering
        with self._active_vis_fb.bind():
            glUseProgram(_VIS_FILTER_PROGRAM.get(VS_OUTPUT_UV=0)) 
            glBindTextureUnit(0, self._filt_active_vis.texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 3)

        # Update history
        glViewport(0, 0, VIS_HISTORY_X, VIS_HISTORY_Y)
        with self._vis_history_fb.bind():
            glEnable(GL_BLEND)
            glBlendFunc(GL_ONE, GL_ONE)
            glBlendEquation(GL_MAX)
            glUseProgram(_VIS_UPDATE_HISTORY_PROGRAM.one())
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters) 
            glBindTextureUnit(1, self._active_vis.texture)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_TRIANGLES, 0, 6)
            glDisable(GL_BLEND)

        glViewport(0, 0, wnd.width, wnd.height)
        glUseProgram(_DEBUG_TEST_BACKGROUND_NORMALS_PROGRAM.get(VS_OUTPUT_UV=0,))
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
        glBindBufferBase(GL_UNIFORM_BUFFER, 1, self._player_pos)
        glBindTextureUnit(2, self._active_background_map_base.texture)
        glBindTextureUnit(3, self._active_background_map_norm.texture)
        glBindTextureUnit(4, self._active_vis.texture)
        glBindTextureUnit(5, self._direct_lighting_bg_map_v0.texture)
        glBindTextureUnit(6, self._direct_lighting_bg_map_v1.texture)
        glBindTextureUnit(7, self._direct_lighting_bg_map_v2.texture)
        glBindTextureUnit(8, self._vis_history.texture)
        glDrawArrays(GL_TRIANGLES, 0, 3)

        # Draw df hits (use df for weapon hitting)
        if False:
            glEnable(GL_BLEND)
            glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
            glBlendEquation(GL_FUNC_ADD)
            glUseProgram(_DEBUG_TEST_DF_PROGRAM.get(VS_OUTPUT_UV=0,))
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindBufferBase(GL_UNIFORM_BUFFER, 1, self._player_pos)
            glBindTextureUnit(2, self._df_bg_map.texture)
            glDrawArrays(GL_TRIANGLES, 0, 3)
            glDisable(GL_BLEND)

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
            self._dirty_load_level = True
            self._dirty_init_levels = True
            print("RECOMPILIN SHADERS")
            wnd.redraw()
            return

        elif key == b'x':
            self._draw_lines ^= 1
            wnd.redraw()
            return

        elif key == b'l':
            self._vis_pf_level = (self._vis_pf_level + 1) & 7
            self._dirty_load_level = True
            print("Level =", self._vis_pf_level)
        # ctrl+l
        elif key == b'\x0c':
            self._vis_pf_level = 0
            self._dirty_load_level = True
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
            self._dirty_init_levels = True

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
