import os
from numpy import *

_SHADER_DIR = os.path.abspath(
    os.path.join(__file__, "..", "shaders", "pointlights_v1")
)


GEN_PLANE_MAP_FRAG = os.path.join(_SHADER_DIR, "gen_plane_map.frag")
GEN_BBOX_FROM_PLANE_MAP_FRAG = os.path.join(_SHADER_DIR, "gen_bbox_from_plane_map.frag")
DRAW_BBOX_VERT = os.path.join(_SHADER_DIR, "draw_bbox.vert")
DRAW_BBOX_FRAG = os.path.join(_SHADER_DIR, "draw_bbox.frag")

DRAW_LIGHTS_VERT = os.path.join(_SHADER_DIR, "draw_lights.vert")
DRAW_LIGHTS_FRAG = os.path.join(_SHADER_DIR, "draw_lights.frag")
DRAW_LIGHTS_FULLSCREEN_VERT = os.path.join(_SHADER_DIR, "draw_lights_fullscreen.vert")


def pack_r11g11b10(value):
    value = array(value, dtype=float16).view(uint16).astype(int)
    value[0] <<= 17
    value[1] <<= 6
    value[2] >>= 5
    value &= (0xffe00000, 0x001ffc00, 0x000003ff)
    return value[0] | value[1] | value[2]


class PointLightData(object):

    def __init__(
            self,
            position=(0.5, 0.5),
            decay_rate=1.0,
            colour=(1.0, 1.0, 1.0)
        ):
        self.position = position
        self.decay_rate = decay_rate
        self.colour = colour

    def pack(self):
        return array((
            float32(self.position[0]).view(uint32),
            float32(self.position[1]).view(uint32),
            float32(self.decay_rate).view(uint32),
            uint32(pack_r11g11b10(self.colour))
        ), dtype=uint32)

    @staticmethod
    def pack_stream(entries):
        return stack([entry.pack() for entry in entries]).flatten()
