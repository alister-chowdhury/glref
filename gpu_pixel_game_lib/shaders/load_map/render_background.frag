#version 460 core

#include "../map_atlas_common.glsli"

#define DF_TEXTURE_BINDING 5
#include "../df_tracing.glsli"

readonly layout(binding=3, rgba8) uniform image2D assetBaseAtlas;
readonly layout(binding=4, rgba8) uniform image2D assetNormAtlas;

layout(location=0) in vec3 pixelCoordAndHeight;
layout(location=1) in vec2 uv;
layout(location=0) out vec4 outBase;
layout(location=1) out vec4 outNormals;

void main()
{
    ivec2 coord = ivec2(pixelCoordAndHeight.xy);

    // Sample from the base of walls, rather than the
    // line itself.
    float AO = df_sample(uv + vec2(0, 0.5 / BACKGROUND_TILE_DIM));
    AO = (sqrt(AO) * 5.0 + 0.4);
    AO = clamp(AO, 0.0, 1.0);

    // Decrease AO up walls
    AO = mix(AO, 1, pixelCoordAndHeight.z);

    outBase = imageLoad(assetBaseAtlas, coord) * vec4(vec3(AO), 1);
    outNormals = vec4(imageLoad(assetNormAtlas, coord).xyz, pixelCoordAndHeight.z);
}
