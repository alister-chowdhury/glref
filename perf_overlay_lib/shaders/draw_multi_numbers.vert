#version 460

#include "number_encoding.glslh"


#ifndef INPUT_IS_ENCODED
#define INPUT_IS_ENCODED 0
#endif


struct NumbersDataEntry
{
    vec4    bounds;

    // .x = number (can be int, uint or float)
    // .y = numberType (0 = int, 1 = uint, 2 = float)
    // .z = packedBgCol (8bit RGBA)
    // .w = packedFgCol (8bit RGBA)
    uvec4   data;
};


layout(std430, binding = 0) buffer numbersDataEntries_
{
    NumbersDataEntry numbersDataEntries[];
};


noperspective layout(location = 0) out vec2 uv;
flat layout(location = 1) out uint encodedNumber;
flat layout(location = 2) out vec4 bgCol;
flat layout(location = 3) out vec4 fgCol;


const uint triangleVertexToQuad[6] = uint[6](
    0, 1, 2,
    2, 1, 3
);


void main()
{
    NumbersDataEntry numberDataEntry = numbersDataEntries[gl_VertexID / 6];

    bgCol = unpackUnorm4x8(numberDataEntry.data.z);
    fgCol = unpackUnorm4x8(numberDataEntry.data.w);

    const uint quadId = triangleVertexToQuad[gl_VertexID % 6];

    uv = vec2(float(quadId & 1), float(quadId >> 1));

    vec2 screenPos = mix(numberDataEntry.bounds.xy, numberDataEntry.bounds.zw, uv);
    gl_Position = vec4(screenPos * 2.0 - 1.0, 0.0, 1.0);

    uint number = numberDataEntry.data.x;

#if INPUT_IS_ENCODED

    encodedNumber = number;

#else

    uint numberType = numberDataEntry.data.y;
    switch(numberType)
    {
        case 0: encodedNumber = encodeNumber(floatBitsToInt(uintBitsToFloat(number))); break;
        case 1: encodedNumber = encodeNumber(number); break;
        default: encodedNumber = encodeNumber(uintBitsToFloat(number)); break;
    }

#endif

}
