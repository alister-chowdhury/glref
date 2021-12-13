#version 460 core

#include "number_encoding.glslh"


noperspective layout(location = 0) in vec2 uv;
flat layout(location = 1) in uint encodedNumber;
flat layout(location = 2) in vec4 bgCol;
flat layout(location = 3) in vec4 fgCol;


layout(location = 0)        out vec4 outCol;


void main()
{
    uint signedValue = sampleEncodedNumber(encodedNumber, uv);
    outCol = (signedValue == 0) ? bgCol : fgCol;
}
