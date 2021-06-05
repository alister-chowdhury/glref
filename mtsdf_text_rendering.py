from math import cos, sin, pi

import struct

import numpy

from OpenGL.GL import *

import viewport


DRAW_PACKED_CHARACTERS_VERTEX_SHADER_SOURCE = """
#version 460 core


// Store 4 characters, with an offset to be drawn sequentially.
struct FourCharactersBlock
{
    vec2    topLeft;
    uvec2   characters;
};


readonly layout (r16ui, binding = 0)  uniform uimage2D indirect;
readonly layout (std430, binding = 2) buffer _characterBlocks { FourCharactersBlock characterBlocks[]; };

layout (location = 0) uniform vec2 characterScreenSize;
layout (location = 2) uniform vec2 unitRange;

noperspective layout(location = 0) out vec3 outUvw;

const uint triangleVertexToQuad[6] = uint[6](
    0, 1, 2,
    2, 1, 3
);


vec3 getCharacterCoord(const uvec2 characters, uint idx)
{
    // Pick the first two characters or bottom two.
    // Then pick the lower or upper character in that pair.
    // Convert that into X,Y coordinates and sample the indirect texture
    // Fetch the pixel there and return back normalised uvw coordinates
    // for use in a texture array.
    const uint  pair           = mix(characters.x, characters.y, bool(idx >> 1));
    const uint  character      = mix(pair & 0xffff, pair >> 16, bool(idx & 1));
    const uint  packedLocation = imageLoad(indirect, ivec2(character & 0xff, character >> 8)).r;
    const uvec3 uvw            = uvec3(
        bitfieldExtract(packedLocation, 0, 5),
        bitfieldExtract(packedLocation, 5, 4),
        bitfieldExtract(packedLocation, 9, 7)
    );

    // X = [0, 32], Y = [0, 16], Z = [0, 127]
    return vec3(uvw) * vec3(0.03125, 0.0625, 1.0);
}


void main()
{

    const uint characterId          = gl_VertexID / 6;
    const uint chracterVertId       = triangleVertexToQuad[gl_VertexID % 6];
    const uint characterBlockId     = characterId >> 2;
    const uint characterSubBlockId  = characterId & 3;

    const FourCharactersBlock characterBlock = characterBlocks[characterBlockId];
    
    vec3  characterUvw  = getCharacterCoord(characterBlock.characters, characterSubBlockId);
    vec2  screenUv      = characterBlock.topLeft
                        + vec2(characterScreenSize.x * float(characterSubBlockId.x), characterScreenSize.y);

    // If we're drawing (0, 0, 0), this means we're drawing a blank region, as such
    // rather than allowing it to fully evaluate, we opt to draw a quad with an area of 0
    // meaning it should get discarded.
    if(characterUvw != vec3(0))
    {
        characterUvw.xy += unitRange;
        characterUvw.x += (0.03125 - 2 * unitRange.x) * float(chracterVertId & 1);
        characterUvw.y += (0.0625 - 2 * unitRange.y)  * float(chracterVertId >> 1);
        screenUv.x     += characterScreenSize.x * float(chracterVertId & 1);
        screenUv.y     += characterScreenSize.y * float(chracterVertId >> 1);
    }

    outUvw      = characterUvw;
    gl_Position = vec4(screenUv * 2.0 - 1.0, 0.0, 1.0);
}


"""


DRAW_CHARACTERS_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout (binding = 1) uniform sampler2DArray characterLayers;

layout (location = 1) uniform vec4 textColour;

// vec2 unitRange = vec2(pxRange)/vec2(textureSize(msdf, 0));
layout (location = 2) uniform vec2 unitRange;

noperspective layout(location = 0) in vec3 uvw;

layout (location = 0) out vec4 outCol;


float median(vec3 value)
{
    return max(min(value.r, value.g), min(max(value.r, value.g), value.b));
}

float screenPxRange()
{
    vec2 screenTexSize = vec2(1.0)/fwidth(uvw.xy);
    return max(0.5*dot(unitRange, screenTexSize), 1.0);
}


void main()
{
    vec4 msdfgen = texture(characterLayers, uvw);
    if(msdfgen.w == 0)
    {
        outCol = vec4(0);
        return;
    }

    float sd = median(msdfgen.xyz);
    float screenPxDistance = screenPxRange()*(sd - 0.5);
    float opacity = clamp(screenPxDistance + 0.5, 0.0, 1.0);
    outCol = opacity * textColour;
}


"""


class FontData(object):
    """Class for interacting with packed font data."""

    def __init__(self, filepath):
        """Initializer.

        Args:
            filepath (str): Path to the packed font file.
        """
        with open(filepath, "rb") as in_fp:
            self.width, self.height, self.layers, self.pixel_range = struct.unpack(
                "HHBB", in_fp.read(6)
            )
            self.character_width = self.width // 32 - 2 * self.pixel_range
            self.character_height = self.height // 16 - 2 * self.pixel_range
            self.layer_pixel_count = self.width * self.height
            self.layer_byte_size = self.layer_pixel_count * 4

            indirect_data = in_fp.read(256 * 256 * 2)
            character_data = in_fp.read(self.layer_byte_size * self.layers)
        self._indirect_ptr = ctypes.c_int()
        self._characters_ptr = ctypes.c_int()

        glCreateTextures(GL_TEXTURE_2D, 1, self._indirect_ptr)
        self.indirect = self._indirect_ptr.value
        glTextureParameteri(self.indirect, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self.indirect, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self.indirect, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTextureParameteri(self.indirect, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glTextureStorage2D(self.indirect, 1, GL_R16UI, 256, 256)
        glTextureSubImage2D(
            self.indirect,
            0,
            0,
            0,
            256,
            256,
            GL_RED_INTEGER,
            GL_UNSIGNED_SHORT,
            indirect_data,
        )

        glCreateTextures(GL_TEXTURE_2D_ARRAY, 1, self._characters_ptr)
        self.characters = self._characters_ptr.value
        glTextureParameteri(self.characters, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self.characters, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self.characters, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTextureParameteri(self.characters, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTextureParameteri(self.characters, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTextureStorage3D(
            self.characters, 1, GL_RGBA8, self.width, self.height, self.layers
        )
        glTextureSubImage3D(
            self.characters,
            0,
            0,
            0,
            0,
            self.width,
            self.height,
            self.layers,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            character_data,
        )


class TextWriterBuffer(object):
    def __init__(self, font_data, origin_is_top_left=True):
        self._entries = []
        self._font_data = font_data
        self._char_aspect_ratio = font_data.character_height / font_data.character_width
        self._screen_aspect_ratio = 1
        self._origin_is_top_left = origin_is_top_left
        self._char_width = 0.01
        self._char_height = self._char_width * self._char_aspect_ratio
        # By default OpenGL starts from bottom left
        if origin_is_top_left:
            self._char_height = -self._char_height
        self._ubo = None
        self._ubo_capacity = 0

    def change_font_size(self, width, height=None):
        if not height:
            height = width * self._char_aspect_ratio
        if self._origin_is_top_left:
            height = -abs(height)
        self._char_width = width
        self._char_height = height

    def change_screen_aspect_ratio(self, aspect_ratio):
        self._screen_aspect_ratio = aspect_ratio

    @staticmethod
    def _make_entry(x, y, a=0, b=0, c=0, d=0):
        return struct.pack("ffHHHH", x, y, a, b, c, d)

    def prepare_text(self, x, y, text):
        # By default OpenGL starts from bottom left
        if self._origin_is_top_left:
            y = (1 - y) - self._char_height
        lines = text.split("\n")
        for line in lines:
            # TODO cull lines offscreen
            chunks = (line[i : i + 4] for i in range(0, len(line), 4))
            for group_id, chunk in enumerate(chunks):
                target_x = (
                    x + self._char_width * 4 * group_id * self._screen_aspect_ratio
                )

                # Offscreen culling X
                if target_x > 1.0:
                    break
                self._entries.append(
                    self._make_entry(target_x, y, *(ord(c) for c in chunk))
                )
            y += self._char_height

            # Offscreen culling Y
            if self._origin_is_top_left:
                if y <= 0.0:
                    break
            elif y >= 1.0:
                break

    def draw(self, colour):

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if self._entries:

            data_size = len(self._entries) * 4 * 4

            # Reallocate if needed
            if self._ubo_capacity < data_size:
                ubo_ptr = ctypes.c_int()
                if self._ubo is not None:
                    ubo_ptr = self._ubo
                    glDeleteBuffers(1, ubo_ptr)
                glCreateBuffers(1, ubo_ptr)
                self._ubo = ubo_ptr.value
                self._ubo_capacity = data_size
                glNamedBufferStorage(
                    self._ubo,
                    data_size,
                    b"".join(self._entries),
                    GL_DYNAMIC_STORAGE_BIT,
                )
            else:
                glNamedBufferSubData(self._ubo, 0, data_size, b"".join(self._entries))
            glBindImageTexture(
                0, self._font_data.indirect, 0, GL_FALSE, 0, GL_READ_ONLY, GL_R16UI
            )
            glBindTextureUnit(1, self._font_data.characters)
            glBindBufferRange(GL_SHADER_STORAGE_BUFFER, 2, self._ubo, 0, data_size)
            glUniform2f(
                0, self._char_width * self._screen_aspect_ratio, self._char_height
            )
            glUniform4f(1, colour[0], colour[1], colour[2], colour[3])
            glUniform2f(
                2,
                self._font_data.pixel_range / self._font_data.width,
                self._font_data.pixel_range / self._font_data.height,
            )
            triangle_count = 6 * 4 * len(self._entries)
            glDrawArrays(GL_TRIANGLES, 0, triangle_count)
            self._entries = []


class Renderer(object):
    def __init__(self):

        self.window = viewport.Window()

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

    def run(self):
        self.window.run()

    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glDisable(GL_CULL_FACE)

        self.font_data = FontData("data/DejaVuSansMono.utf8.fnt")

        self.text_writer = TextWriterBuffer(self.font_data)

        self._draw_text_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=DRAW_PACKED_CHARACTERS_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=DRAW_CHARACTERS_FRAGMENT_SHADER_SOURCE,
        )

        dummy_vao_ptr = ctypes.c_int()
        glCreateVertexArrays(1, dummy_vao_ptr)
        self._dummy_vao = dummy_vao_ptr.value
        glViewport(0, 0, wnd.width, wnd.height)

    def _draw(self, wnd):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Read and draw this file
        target_file = __file__
        with open(target_file, "r") as in_fp:
            text = (
                in_fp.read()
                .replace("\n\n\n\n", "\n")
                .replace("\n\n\n", "\n")
                .replace("\n\n", "\n")
            )
        self.text_writer.prepare_text(0, 0, text)

        glUseProgram(self._draw_text_program)
        glBindVertexArray(self._dummy_vao)
        self.text_writer.draw((0, 1, 0, 1))

    def _resize(self, wnd, width, height):
        glViewport(0, 0, width, height)
        self.text_writer.change_screen_aspect_ratio(height / width)

    def _keypress(self, wnd, key, x, y):
        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()
