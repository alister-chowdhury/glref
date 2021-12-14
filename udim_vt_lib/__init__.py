
from . _imageio_pil import Image
from . indirection import (
    UdimIndirectionBuilder,
    UdimEntry
)


import os
_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders")
)

APPLY_VT_TEXTURES_PATH = os.path.join(_SHADER_DIR, "apply_vt_textures.comp")

with open(APPLY_VT_TEXTURES_PATH, "r") as in_fp:
    APPLY_VT_TEXTURES_CS = in_fp.read()
