#version 460 core

#include "../common.glsli"
#include "../map_atlas_common.glsli"

#define DF_TEXTURE_BINDING 2
#include "../df_tracing.glsli"

layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
};

layout(set=0, binding = 1) uniform playerPos_
{
    vec2 playerPos;
};

layout(location=0) in vec2    uv;
layout(location=0) out vec4   outCol;

void main()
{

    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);
    float levelToScreenScale = getLevelToBackgroundScale(atlasInfo);

    vec2 scaledUv = uv * levelToScreenScale;

    vec2 fromTarget = scaledUv - playerPos;
    float dist = length(fromTarget); 
    DFTraceResult trace = df_trace(playerPos, fromTarget / dist, dist);
    outCol = vec4(1.0, 0.0, 0.0, 1.0) * float(trace.visible);
}
