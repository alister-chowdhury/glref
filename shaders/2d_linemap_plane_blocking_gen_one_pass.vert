#version 460 core

#include "common.glsl"

layout(location=0)  uniform ivec2 numLightsAndLines;

layout(location=0) out vec2 angleAndLightId;

void main()
{
    vec2 ndc;
    
    switch(gl_VertexID & 3)
    {
        case 0: { ndc = vec2(-4, -1); break; }
        case 1: { ndc = vec2(1, -1); break; }
        case 2: { ndc = vec2(1, 4); break; }
    }

    angleAndLightId = vec2(ndc.x * PI, (ndc.y * 0.5 + 0.5) * numLightsAndLines.x);
    gl_Position = vec4(ndc, 0., 1.);
}
