#version 460 core

#include "../common.glsli"

layout(binding=1) uniform sampler2D visibility;
layout(location=0) in vec2  sourceCord;
layout(location=0) out float outVisibility;

void main()
{
    outVisibility = texelFetch(visibility, ivec2(sourceCord), 0).x;
}
