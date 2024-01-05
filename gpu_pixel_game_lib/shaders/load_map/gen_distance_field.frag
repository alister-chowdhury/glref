#version 460 core

#define LINE_BVH_V2_BINDING 0
#include "../v2_tracing.glsli"

layout(location=0) in vec2 uv;
layout(location=0) out float outDf;

void main()
{
    float df = findNearestDistanceBvhV2(uv, 3.0);
    outDf = df;
}
