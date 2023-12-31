#version 460 core

#include "../common.glsli"

layout(binding=0) uniform sampler2D directLightingV0;
layout(binding=1) uniform sampler2D directLightingV1;
layout(binding=2) uniform sampler2D directLightingV2;

layout(location=0) in vec2  uv;

layout(location=0) out vec3   outV0;
layout(location=1) out vec4   outV1;
layout(location=2) out vec2   outV2;

void main()
{
    vec3 accumV0 = vec3(0);
    vec4 accumV1 = vec4(0);
    vec2 accumV2 = vec2(0);
    float weight = 0.0;

    // We know the exact size of this, swap it out
    // when we're sure everything is fine.
    vec2 duv = vec2(dFdx(uv.x), dFdy(uv.y));

    for(float dX=-1; dX<=1; ++dX)
    for(float dY=-1; dY<=1; ++dY)
    {
        // Should rally use texelFetch...
        float w = 1.0 / (length(vec2(dX, dY)) + 1.0);
        accumV0 += texture(directLightingV0, uv + vec2(dX, dY) * duv).xyz   * w;
        accumV1 += texture(directLightingV1, uv + vec2(dX, dY) * duv).xyzw  * w;
        accumV2 += texture(directLightingV2, uv + vec2(dX, dY) * duv).xy    * w;
        weight += w;
    }

    outV0 = accumV0 / weight;
    outV1 = accumV1 / weight;
    outV2 = accumV2 / weight;
}
