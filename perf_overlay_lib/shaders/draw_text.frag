#version 460 core


#ifndef ASCII
#define ASCII 0
#endif

#if ASCII
#define TEXT_DATA_DEFAULT_ASCII 1
#else
#define TEXT_DATA_DEFAULT_ASCII 0
#endif


#include "font_data.glslh"


noperspective layout(location = 0) in vec2 inUv;
flat layout(location = 1) in uint chractersOffset;
flat layout(location = 2) in float numCharacters;
flat layout(location = 3) in vec4 fgCol;
flat layout(location = 4) in vec4 bgCol;


layout(location = 0)        out vec4 outCol;


readonly layout(std430, binding = 0) buffer fontData_
{
    FontDataHeader fontDataHeader;
    uint           fontData[];
};

readonly layout(std430, binding = 1) buffer textData_
{
    uint           textData[];
};


void main()
{
    vec2 uv = inUv * vec2(numCharacters, 1.);
    uint characterId = uint(uv.x);
    uv.x = fract(uv.x);

#if ASCII

    uint offset = (characterId / 4);
    uint shift = (characterId % 4) * 8;
    uint character = (
        textData[chractersOffset + offset] >> shift
    ) & 0xff;

#else

    uint offset = (characterId / 2);
    uint shift = (characterId % 2) * 16;
    uint character = (
        textData[chractersOffset + offset] >> shift
    ) & 0xffff;

#endif

    uint signedValue = sampleTextData(
        character,
        uv,
        fontDataHeader,
        fontData
    );

    outCol = (signedValue == 0) ? bgCol : fgCol;

}