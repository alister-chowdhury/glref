#version 460 core

#include "common.glsli"

layout(binding=0) uniform usampler2D atlasMap;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec4 value;

void main()
{
    uint v = texture(atlasMap, uv).x;
    vec3 c = randomHs1Col(v);
    if(v == 0u)
    {
        c = vec3(0);
    }
    else if(v == 1u || v == 2u)
    {
        c = vec3(1.);
    }
    // else if(v >= 31u)
    // {
    //     c = vec3(1.0);
    // }
    value = vec4(c, 1.0);
}
