#version 460 core

layout(binding=4) uniform sampler2D assetBaseAtlas;

layout(location=0) in vec2 uv;
layout(location=0) out vec4 outCol;

void main()
{
    vec4 result = textureLod(assetBaseAtlas, uv, 0);
    result.xyz *= result.w;
    outCol = vec4(result);
}
