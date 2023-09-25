
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
            self._vis_pf_room = (self._vis_pf_room + 1) & 63
            print("Room =", self._vis_pf_room + 1)
        # ctrl+o
        elif key == b'\x0f':
            self._vis_pf_room = 0
            print("Room =", self._vis_pf_room + 1)

        elif key == b'c':
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
            glNamedBufferStorage(self._global_parameters, len(global_parameters), global_parameters, 0)

            self._n += 1

        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height
        wnd.redraw()

if __name__ == "__main__":
    Renderer().run()
