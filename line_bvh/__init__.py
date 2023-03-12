import os
from .v1 import build_line_bvh_v1

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

V1_DRAW_BVH_VERT = os.path.join(_SHADER_DIR, "v1_draw_bvh.vert")
V1_DRAW_BVH_FRAG = os.path.join(_SHADER_DIR, "v1_draw_bvh.frag")
V1_TRACING_TEST_FRAG = os.path.join(_SHADER_DIR, "v1_tracing_test.frag")


# Not good it turns out
ANISO_DF_DOWNRES_FRAG = os.path.join(_SHADER_DIR, "aniso_df_downres.frag")
ANISO_DF_GENERATION_FRAG = os.path.join(_SHADER_DIR, "aniso_df_generation.frag")
ANISO_DF_TRACING_TEST_FRAG = os.path.join(_SHADER_DIR, "aniso_df_tracing_test.frag")


# Better, could probably make a faster generation via the BVH
DF_DOWNRES_FRAG = os.path.join(_SHADER_DIR, "df_downres.frag")
DF_GENERATION_FRAG = os.path.join(_SHADER_DIR, "df_generation.frag")
DF_TRACING_TEST_FRAG = os.path.join(_SHADER_DIR, "df_tracing_test.frag")
