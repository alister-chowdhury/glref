#version 460 core


#include "common.glsli"


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 


readonly layout(std430, binding = 1) buffer lines_ { vec4 lines[]; };


void main()
{
    vec4 line = lines[gl_VertexID / 2];
    vec2 P = ((gl_VertexID & 1) == 0) ? line.xy : line.zw;
    gl_Position = vec4(P * 2.0 - 1.0, 0.0, 1.0);
}

