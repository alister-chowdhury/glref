#version 460 core

#include "../common.glsli"
#include "../map_atlas_common.glsli"

layout(binding=0) uniform sampler2D visibility;

layout(location=0) in vec2  uv;

layout(location=0) out float outVisibility;

void main()
{
    float accumVis = 0;
    float weight = 0.0;

    vec2 duv = vec2(1.0 / ACTIVE_VIS_SIZE);

    for(float dX=-4; dX<=4; ++dX)
    for(float dY=-4; dY<=4; ++dY)
    {
        // Should rally use texelFetch...
        float w = 1.0 / (length(vec2(dX, dY)) + 1.0);
        accumVis += texture(visibility, uv + vec2(dX, dY) * duv).x * w;
        weight += w;
    }

    outVisibility = accumVis / weight;
}
