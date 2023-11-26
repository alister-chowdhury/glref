import os
from .v1 import build_line_df_hybrid_v1

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

V1_TRACING_TEST_FRAG = os.path.join(_SHADER_DIR, "v1_tracing_test.frag")
