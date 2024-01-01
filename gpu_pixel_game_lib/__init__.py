import os

_ASSETS_DIR = os.path.abspath(
    os.path.join(__file__, "..", "assets")
)
_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)
_OLD_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders", "_OLD")
)



GENERATE_MAP_LINES_COMP__OLD = os.path.join(_OLD_SHADER_DIR, "generate_map_lines.comp")

DRAW_LINES_DEBUG_VERT__OLD = os.path.join(_OLD_SHADER_DIR, "draw_lines_debug.vert")
DRAW_LINES_DEBUG_FRAG__OLD = os.path.join(_OLD_SHADER_DIR, "draw_lines_debug.frag")
DRAW_BSP_MAP_DEBUG_FRAG = os.path.join(_OLD_SHADER_DIR, "draw_bsp_map_debug.frag")

DRAW_BVH_DEBUG_VERT = os.path.join(_OLD_SHADER_DIR, "draw_bvh_debug.vert")
DRAW_BVH_DEBUG_FRAG = os.path.join(_OLD_SHADER_DIR, "draw_bvh_debug.frag")


ASSET_ATLAS_DATA = os.path.join(_ASSETS_DIR, "ASSET_ATLAS.dat")
ASSET_ATLAS_BASE = os.path.join(_ASSETS_DIR, "ATLAS_BASE.png")
ASSET_ATLAS_NORM = os.path.join(_ASSETS_DIR, "ATLAS_NORM.png")


GEN_MAP_ATLAS_COMP = os.path.join(_SHADER_DIR, "initlevels", "gen_map_atlas.comp")
GEN_PATHFINDING_DIRECTIONS_COMP = os.path.join(_SHADER_DIR, "initlevels", "gen_pathfinding_directions.comp")
FINISH_MAP_GEN_COMP = os.path.join(_SHADER_DIR, "initlevels", "finish_map_gen.comp")
VIS_CLEAR_HISTORY_FRAG = os.path.join(_SHADER_DIR, "initlevels", "vis_clear_history.frag")

DEBUG_VIS_PATHFINDING_DIRECTIONS_VERT = os.path.join(_SHADER_DIR, "initlevels", "debug_vis_pathfinding_directions.vert")
DEBUG_VIS_PATHFINDING_DIRECTIONS_FRAG = os.path.join(_SHADER_DIR, "initlevels", "debug_vis_pathfinding_directions.frag")

RENDER_MAP_BACKGROUND_VERT = os.path.join(_SHADER_DIR, "load_map", "render_background.vert")
RENDER_MAP_BACKGROUND_FRAG = os.path.join(_SHADER_DIR, "load_map", "render_background.frag")
GEN_MAP_LINES_COMP = os.path.join(_SHADER_DIR, "load_map", "gen_map_lines.comp")
GEN_DIRECT_LIGHTING_FRAG = os.path.join(_SHADER_DIR, "load_map", "gen_direct_lighting.frag")
FILTER_DIRECT_LIGHTING_FRAG = os.path.join(_SHADER_DIR, "load_map", "filter_direct_lighting.frag")

DEBUG_DRAW_LINES_VERT = os.path.join(_SHADER_DIR, "load_map", "debug_draw_lines.vert")
DEBUG_DRAW_LINES_FRAG = os.path.join(_SHADER_DIR, "load_map", "debug_draw_lines.frag")


DEBUG_SET_PLAYER_POS_COMP = os.path.join(_SHADER_DIR, "playing", "debug_set_player_pos.comp")
VIS_GENERATE_VERT = os.path.join(_SHADER_DIR, "playing", "vis_generate.vert")
VIS_GENERATE_FRAG = os.path.join(_SHADER_DIR, "playing", "vis_generate.frag")
VIS_GENERATE_CLEAR_FRAG = os.path.join(_SHADER_DIR, "playing", "vis_generate_clear.frag")
VIS_FILTER_FRAG = os.path.join(_SHADER_DIR, "playing", "vis_filter.frag")
VIS_UPDATE_HISTORY_VERT = os.path.join(_SHADER_DIR, "playing", "vis_update_history.vert")
VIS_UPDATE_HISTORY_FRAG = os.path.join(_SHADER_DIR, "playing", "vis_update_history.frag")
DEBUG_TEST_BACKGROUND_NORMALS_FRAG = os.path.join(_SHADER_DIR, "playing", "debug_test_background_normals.frag")
