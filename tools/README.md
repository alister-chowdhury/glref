GL-REF Tools
============

Build instructions
------------------

This builds `msdfgen` and `docopt.cpp` as part of the global build.

You will need to make sure you've updated the submodules:
```
git submodule update --init --recursive
```


If TBB can be found (which requires exporting a TBBConfig.cmake file as part of the build), it can be utilised.

Actual building takes place with CMake

**With Linux (untested) it should be something like**
```
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
```

**With Windows via Vcpkg it should be something like**
```
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=path\to\vcpkg\scripts\buildsystems\vcpkg.cmake
cmake --build . --config Release
```

There is no install setup, it will just always put things in the `bin` directory.


Tools
-----

**indirect-mtsdf-utf8-gen**

Given a TTF file it generates a file containing a indirect texture and a texture array table of glyphs for text rendering (for use with the basic multilanguage plane).
```
    Usage: indirect-mtsdf-utf8-gen (-i FILE) (-o FILE) [-s SCALE] [-p UINT] [--save-temps DIR] [--directx]

    Options:
      -h --help                      Show this screen.
      -i <file>, --input  <file>     Input TTF file.
      -o <file>, --output <file>     Output indirect + MTSDF texture array file.
      -s <scale>, --scale <scale>    How much to scale the font by. [default: 1]
      -p <range>, --pxrange <range>  Pixel range to sample around. [default: 1]
      --save-temps <dir>             Save the layers and indirect texture into a directory.
      --directx                      Flip Y to start at the top left, rather than bottom left.
```

The indirect texture component stores lookups for glyphs via:
```c
// Convert your unicode character to 16bit
uint16 character = ...;
uint16 indirectX = character & 0xff; // lower 8bits
uint16 indirectY = character >> 8;   // upper 8bits

uint16 packedLocation = imageFetch(indirectTexture, indirectX, indirectY);
uint16 tileX = bitfieldExtract(packedLocation, 0, 5); // x => packedLocation[0:5]
uint16 tileY = bitfieldExtract(packedLocation, 5, 4); // y => packedLocation[5:9]
uint16 layer = bitfieldExtract(packedLocation, 9, 7); // layer => packedLocation[9:15]

vec3 tileTopLeft = vec3(
    float(tileX) * 0.03125, // tileX = [0, 32]
    float(tileY) * 0.0625,  // tileY = [0, 16]
    float(layer) // layer = [0, 127]
);
```

The resulting file will have the following layout:
```c
uint16  perLayerWidth;
uint16  perLayerHeight;
uint8   layerCount;
uint8   pixelRange;

uint16  indirectTexture[256 * 256];
uint8   characterLayers[perLayerWidth * perLayerHeight * layerCount];
```

Per character width / height can be computed via:
```c
uint16 characterWidth = perLayerWidth / 32 - 2 * uint16(pixelRange);
uint16 characterHeight = perLayerHeight / 16 - 2 * uint16(pixelRange);
float aspectRatio = float(characterHeight) / float(characterWidth);
```


Which should have a shader mapping of something like:
```glsl
readonly layout (r16ui, binding = 0)  uniform uimage2D indirect;
layout (binding = 1) uniform sampler2DArray characterLayers;
layout (location = 0) uniform vec2 characterScreenSize; // vec2(screenWidth, screenWidth * aspectRatio)
layout (location = 2) uniform vec2 unitRange;           // float(pixelRange) / vec2(perLayerWidth, perLayerHeight)


// VERTEX SHADER
noperspective layout(location = 0) out vec3 outUvw;

vec3 getCharacterCoord(uint character)
{
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
    uint character = ...;
    float right = ...;   // 0 = left, 1 = right
    float top = ...;     // 0 = bottom, 1 = top
    vec2 screenUv = ...;

    vec3  characterUvw  = getCharacterCoord(character);

    // If we're drawing (0, 0, 0), this means we're drawing a blank region, as such
    // rather than allowing it to fully evaluate, we opt to draw a quad with an area of 0
    // meaning it should get discarded.
    if(characterUvw != vec3(0))
    {
        characterUvw.xy += unitRange;
        characterUvw.x += (0.03125 - 2 * unitRange.x) * right;
        characterUvw.y += (0.0625 - 2 * unitRange.y)  * top;
        screenUv.x     += characterScreenSize.x * right;
        screenUv.y     += characterScreenSize.y * top;
    }

    outUvw      = characterUvw;
    gl_Position = vec4(screenUv * 2.0 - 1.0, 0.0, 1.0);
}


// VERTEX SHADER

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
    vec4 textColour = ...;

    vec4 msdfgen = texture(characterLayers, uvw);
    // Early exit is signed distance is 0
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

```

