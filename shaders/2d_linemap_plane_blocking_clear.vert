#version 460 core

#include "common.glsl"


layout(location=0) out float angle;

void main()
{
    vec2 ndc;
    
    switch(gl_VertexID & 3)
    {
        case 0: { ndc = vec2(-4, -1); break; }
        case 1: { ndc = vec2(1, -1); break; }
        case 2: { ndc = vec2(1, 4); break; }
    }

    angle = ndc.x * PI;
    gl_Position = vec4(ndc, 1., 1.);
}
