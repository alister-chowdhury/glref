#version 460 core


#include "../common.glsli"
#include "../map_atlas_common.glsli"


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 


         layout(binding = 1)         uniform numLines_ { uint numLines; };
readonly layout(std430, binding = 2) buffer lines_     { vec4 lines[]; };


void main()
{
    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);
    float backgroundToLevel = getBackgroundToLevelScale(atlasInfo);

    uint lineId = gl_VertexID / 2;
    if(lineId < numLines)
    {
        vec4 line = lines[gl_VertexID / 2];
        vec2 P = ((gl_VertexID & 1) == 0) ? line.xy : line.zw;
        P *= backgroundToLevel;
        gl_Position = vec4(P * 2.0 - 1.0, 0.0, 1.0);
    }
}

