#version 460 core

#include "../common.glsl"

readonly layout(std430, binding = 0) buffer lines_ { vec4 lines[]; };
layout(location=0) out vec3 col;


void main()
{
    int side = gl_VertexID % 2;
    vec4 line = lines[gl_VertexID / 2];
    vec2 uv = side == 0 ? line.xy : line.zw;
    col = vec3(1.0);
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}

