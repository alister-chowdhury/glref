#version 460 core


layout(location=COLOUR_LOCATION) uniform vec4 inCol;
layout(location=0) out vec4 outCol;


void main()
{
    outCol = inCol;
}
