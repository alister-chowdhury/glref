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


UNIFORM_PROBE_NEIGHBOUR_VISIBILITY_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_neighbour_visibility_df.frag")
UNIFORM_PROBE_VISIBILITY_DISTANCES_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_visibility_distances.frag")
UNIFORM_PROBE_RADIANCE_SAMPLE_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_radiance_sample.frag")
UNIFORM_PROBE_SPATIAL_FILTER_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_spatial_filter.frag")
UNIFORM_PROBE_CH_INTEGRATE_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_ch_integrate.frag")
UNIFORM_PROBE_INDIRECT_DIFFUSE_SAMPLE_RADIANCE_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_indirect_diffuse_sample_radiance.frag")


UNIFORM_PROBE_SPHERE_TEST_VERT = os.path.join(_SHADER_DIR, "uniform_probe_sphere_test.vert")
UNIFORM_PROBE_SPHERE_TEST_FRAG = os.path.join(_SHADER_DIR, "uniform_probe_sphere_test.frag")
