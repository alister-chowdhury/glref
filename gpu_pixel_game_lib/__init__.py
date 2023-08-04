import os

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)
_OLD_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders", "_OLD")
)


GENERATE_MAP_BSP_COMMANDS_COMP = os.path.join(_OLD_SHADER_DIR, "generate_map_bsp_commands.comp")
GENERATE_MAP_BSP_DRAW_VERT = os.path.join(_OLD_SHADER_DIR, "generate_map_bsp_draw.vert")
GENERATE_MAP_BSP_DRAW_FRAG = os.path.join(_OLD_SHADER_DIR, "generate_map_bsp_draw.frag")
GENERATE_MAP_LINES_COMP = os.path.join(_OLD_SHADER_DIR, "generate_map_lines.comp")

DRAW_LINES_DEBUG_VERT = os.path.join(_OLD_SHADER_DIR, "draw_lines_debug.vert")
DRAW_LINES_DEBUG_FRAG = os.path.join(_OLD_SHADER_DIR, "draw_lines_debug.frag")
DRAW_BSP_MAP_DEBUG_FRAG = os.path.join(_OLD_SHADER_DIR, "draw_bsp_map_debug.frag")

GENERATE_MAP_BVH_COMP____WIP = os.path.join(_OLD_SHADER_DIR, "generate_map_bvh__wip_v1.comp")
GENERATE_MAP_BVH_V2_COMP = os.path.join(_OLD_SHADER_DIR, "generate_map_bvh_v2.comp")

DRAW_BVH_DEBUG_VERT = os.path.join(_OLD_SHADER_DIR, "draw_bvh_debug.vert")
DRAW_BVH_DEBUG_FRAG = os.path.join(_OLD_SHADER_DIR, "draw_bvh_debug.frag")