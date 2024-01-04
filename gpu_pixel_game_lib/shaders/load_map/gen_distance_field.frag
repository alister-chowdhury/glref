#version 460 core

#include "../map_atlas_common.glsli"

#define LINE_BVH_V2_STACK_SIZE 9
#define LINE_BVH_V2_BINDING 0
// #include "../../../shaders/grid_based_bvh/v2_tracing.glsli"
#include "../v2_tracing.glsli"

layout(location=0) in vec2 uv;
layout(location=0) out float outDf;

void main()
{
    float df = findNearestDistanceBvhV2(uv, 3.0);
    outDf = min(1.0, df);
}
