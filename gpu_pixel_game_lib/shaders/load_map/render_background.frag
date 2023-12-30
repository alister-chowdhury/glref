#version 460 core

#define LINE_BVH_V2_STACK_SIZE 9
#define LINE_BVH_V2_BINDING 5
// #include "../../../shaders/grid_based_bvh/v2_tracing.glsli"
#include "../v2_tracing.glsli"

readonly layout(binding=3, rgba8) uniform image2D assetBaseAtlas;
readonly layout(binding=4, rgba8) uniform image2D assetNormAtlas;

layout(location=0) in vec3 pixelCoordAndHeight;
layout(location=1) in vec2 uv;
layout(location=0) out vec4 outBase;
layout(location=1) out vec4 outNormals;

void main()
{
    ivec2 coord = ivec2(pixelCoordAndHeight.xy);

    float AO = findNearestDistanceBvhV2(uv, 1.0);
    AO = (sqrt(AO) * 2.0 + 0.4);
    AO = clamp(AO, 0.0, 1.0);

    // Decrease AO up walls
    AO = mix(AO, 1, pixelCoordAndHeight.z);

    outBase = imageLoad(assetBaseAtlas, coord) * vec4(vec3(AO), 1);
    outNormals = vec4(imageLoad(assetNormAtlas, coord).xyz, pixelCoordAndHeight.z);
}
