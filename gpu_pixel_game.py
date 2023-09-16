
import os

import numpy

from OpenGL.GL import *

import viewport
import gpu_pixel_game_lib

_DEBUGGING = False


_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

_DRAW_FULL_SCREEN_PATH = os.path.join(
    _SHADER_DIR, "draw_full_screen.vert"
)


_DRAW_LINES_DEBUG_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.DRAW_LINES_DEBUG_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DRAW_LINES_DEBUG_FRAG
)

_DRAW_BSP_MAP_DEBUG_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = _DRAW_FULL_SCREEN_PATH,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DRAW_BSP_MAP_DEBUG_FRAG
)


_GENERATE_MAP_LINES_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GENERATE_MAP_LINES_COMP
)

_GENERATE_MAP_BVH_V2_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GENERATE_MAP_BVH_V2_COMP
)

_DRAW_BVH_DEBUG_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.DRAW_BVH_DEBUG_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DRAW_BVH_DEBUG_FRAG
)

_GEN_MAP_ATLAS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GEN_MAP_ATLAS_COMP
)

_GEN_PATHFINDING_DIRECTIONS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_COMPUTE_SHADER = gpu_pixel_game_lib.GEN_PATHFINDING_DIRECTIONS_COMP
)

_DEBUG_VIS_PATHFINDING_DIRECTIONS_PROGRAM = viewport.make_permutation_program(
    _DEBUGGING,
    GL_VERTEX_SHADER = gpu_pixel_game_lib.DEBUG_VIS_PATHFINDING_DIRECTIONS_VERT,
    GL_FRAGMENT_SHADER = gpu_pixel_game_lib.DEBUG_VIS_PATHFINDING_DIRECTIONS_FRAG
)

LEVEL_TILES_X = 128
LEVEL_TILES_Y = 128


class Renderer(object):


    def __init__(self):

        self.window = viewport.Window(512, 512)

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self._n = 0
        self._vis_pf_level = 0
        self._vis_pf_room = 0

    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)

        # todo record indirection commands etc for indirect drawcalls
        self._buffers_ptr = (ctypes.c_int * 10)()
        glCreateBuffers(10, self._buffers_ptr)


        self._global_parameters = self._buffers_ptr[0]
        self._draw_allocator = self._buffers_ptr[1]
        self._draw_commands = self._buffers_ptr[2]
        self._lines_buffer = self._buffers_ptr[3]
        self._gen_bvh_params_buffer = self._buffers_ptr[4]
        self._bvh_buffer = self._buffers_ptr[5]
        self._generated_lines = self._buffers_ptr[6]


        global_parameters = numpy.array(
            [
                0x12345678, # randomSeed
                0xf01231f0, # levelSeed
                # Padding
                0, 0
            ],
            dtype=numpy.uint32
        ).tobytes()

        draw_indirect = numpy.array(
            [
                0, # vertexCount
                1, # instanceCount
                0, # firstVertex
                0, # firstInstance
            ],
            dtype=numpy.uint32
        ).tobytes()

        lines = (numpy.array(
            [
                0.1, 0.1, 0.5, 0.5,
                0.2, 0.2, 0.6, 0.6,
                0.5, 0.1, 0.5, 0.5,
                0.6, 0.2, 0.6, 0.6,
                0.5, 0.1, 0.5, 0.5,
                0.6, 0.2, 0.6, 0.6,
            ],
            dtype=numpy.float32
            )
         ).tobytes()

        gen_bvh_params = numpy.array(
            [
                len(lines) // (4 * 4), # numLines
                0, # padding
                0, # padding
                0, # padding
            ],
            dtype=numpy.uint32
        ).tobytes()

        glNamedBufferStorage(self._global_parameters, len(global_parameters), global_parameters, 0)
        glNamedBufferStorage(self._draw_allocator, len(draw_indirect), draw_indirect, 0)
        glNamedBufferStorage(self._draw_commands, 4 * 2 * LEVEL_TILES_X * LEVEL_TILES_Y, None, 0)
        glNamedBufferStorage(self._lines_buffer, len(lines), lines, 0)
        glNamedBufferStorage(self._gen_bvh_params_buffer, len(gen_bvh_params), gen_bvh_params, 0)
        glNamedBufferStorage(self._bvh_buffer, 4 * 4 * 3 * 189 + 1024 * 4, None, 0)
        glNamedBufferStorage(self._generated_lines, 4 * 1024, None, 0)


        self._map_atlas_tiles = viewport.FramebufferTarget(GL_R8UI, True)
        self._map_atlas_depth = viewport.FramebufferTarget(GL_DEPTH_COMPONENT32F, True)
        self._map_atlas_fb = viewport.Framebuffer(
            (
                self._map_atlas_tiles,
                self._map_atlas_depth,
            ),
            LEVEL_TILES_X,
            LEVEL_TILES_Y,
        )

        global_parameters2 = numpy.array(
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

        self._buffers2_ptr = (ctypes.c_int * 10)()
        glCreateBuffers(10, self._buffers2_ptr)
        self._global_parameters2 = self._buffers2_ptr[0]
        glNamedBufferStorage(self._global_parameters2, len(global_parameters2), global_parameters2, 0)

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
            LEVEL_TILES_X,
            LEVEL_TILES_Y
        )
        
        glClearTexImage(
            self._pathfinding_directions,
            0,
            GL_RG_INTEGER ,
            GL_UNSIGNED_INT,
            numpy.array([0, 0], dtype=numpy.uint32).tobytes()
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(_GEN_MAP_ATLAS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters2)
        glBindImageTexture(1, self._map_atlas_tiles.texture, 0, False, 0, GL_WRITE_ONLY, GL_R8UI)
        glDispatchCompute(1, 1, 8)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glUseProgram(_GEN_PATHFINDING_DIRECTIONS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters2)
        glBindImageTexture(1, self._map_atlas_tiles.texture, 0, False, 0, GL_READ_ONLY, GL_R8UI)
        glBindImageTexture(2, self._pathfinding_directions, 0, False, 0, GL_READ_WRITE, GL_RG32UI)
        glDispatchCompute(1, 1, 8)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glUseProgram(_DRAW_BSP_MAP_DEBUG_PROGRAM.get(VS_OUTPUT_UV=0))
        glBindTextureUnit(0, self._map_atlas_tiles.texture)
        # glBindTextureUnit(0, self._pathfinding_directions)
        glBindVertexArray(viewport.get_dummy_vao())
        glDrawArrays(GL_TRIANGLES, 0, 3)

        glUseProgram(_DEBUG_VIS_PATHFINDING_DIRECTIONS_PROGRAM.one())
        glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters2)
        glBindImageTexture(1, self._map_atlas_tiles.texture, 0, False, 0, GL_READ_ONLY, GL_R8UI)
        glBindImageTexture(2, self._pathfinding_directions, 0, False, 0, GL_READ_ONLY, GL_RG32UI)
        glUniform2ui(0, self._vis_pf_level, self._vis_pf_room)
        glDrawArrays(GL_TRIANGLES, 0, 64 * 64 * 6)

        if False:
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
            glUseProgram(_GENERATE_MAP_LINES_PROGRAM.one())
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindImageTexture(1, self._map_atlas_tiles.texture, 0, False, 0, GL_READ_ONLY, GL_R8UI)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._draw_allocator)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._generated_lines)
            glDispatchCompute(1, 1, 1)

            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
            glUseProgram(_DRAW_LINES_DEBUG_PROGRAM.one())
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._generated_lines)
            glBindVertexArray(viewport.get_dummy_vao())
            glBindBuffer(GL_DRAW_INDIRECT_BUFFER, self._draw_allocator)
            glDrawArraysIndirect(GL_LINES, ctypes.c_void_p(0))

            glUseProgram(_GENERATE_MAP_BVH_V2_PROGRAM.one())
            glBindBufferBase(GL_UNIFORM_BUFFER, 0, self._global_parameters)
            glBindBufferBase(GL_UNIFORM_BUFFER, 1, self._gen_bvh_params_buffer)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self._lines_buffer)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self._bvh_buffer)
            glDispatchCompute(1, 1, 1)

            # Super broken, we need to start again from scratch really..
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
            glUseProgram(_DRAW_BVH_DEBUG_PROGRAM.one())
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._bvh_buffer)
            glBindVertexArray(viewport.get_dummy_vao())
            glDrawArrays(GL_LINES, 0, 16 * 63)

        wnd.redraw()


    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)

    def _keypress(self, wnd, key, x, y):

        # CTRL-R
        if key == b'\x12':
            viewport.clear_compiled_shaders()

        elif key == b'l':
            self._vis_pf_level = (self._vis_pf_level + 1) & 7
            print("Level =", self._vis_pf_level)
        # ctrl+l
        elif key == b'\x0c':
            self._vis_pf_level = 0
            print("Level =", self._vis_pf_level)

        elif key == b'o':
            self._vis_pf_room = (self._vis_pf_room + 1) & 31
            print("Room =", self._vis_pf_room)
        # ctrl+o
        elif key == b'\x0f':
            self._vis_pf_room = 0
            print("Room =", self._vis_pf_room)

        elif key == b'c':
            glDeleteBuffers(1, self._buffers_ptr)
            glCreateBuffers(1, self._buffers_ptr)
            self._global_parameters = self._buffers_ptr[0]

            global_parameters = numpy.array(
                [
                    self._n, # randomSeed
                    0xf01231f0, # levelSeed
                    # Padding
                    0, 0
                ],
                dtype=numpy.uint32
            ).tobytes()
            glNamedBufferStorage(self._global_parameters, len(global_parameters), global_parameters, 0)

            glDeleteBuffers(1, self._buffers2_ptr)
            glCreateBuffers(1, self._buffers2_ptr)
            self._global_parameters2 = self._buffers2_ptr[0]
            global_parameters2 = numpy.array(
                [
                    0,          # cpuTime
                    0,          # cpuAnimFrame
                    0,          # cpuAnimTick
                    self._n, # cpuRandom

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

            glNamedBufferStorage(self._global_parameters2, len(global_parameters2), global_parameters2, 0)

            self._n += 1

        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height
        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
