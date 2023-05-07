#version 460 core

#include "v1_tracing.glsli"

layout(location=0) in vec2 uv;
layout(location=0) out vec4 col;


void main()
{
    float d = findNearestDistanceBvhV1(uv, 10.0);
    col = vec4(d, d, d, d);
}
