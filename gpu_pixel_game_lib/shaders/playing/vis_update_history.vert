#version 460 core

#include "../common.glsli"
#include "../map_atlas_common.glsli"

layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
};

layout(location=0) out vec2  sourceCord;


void main()
{
    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);

    int quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);
    uvec2 offset = atlasInfo.offset;
    uvec2 size = atlasInfo.size;

    sourceCord = vec2((quadId & 1) == 0 ? 0 : size.x * VIS_BUFFER_TILE_SIZE,
                      (quadId & 2) == 0 ? 0 : size.y * VIS_BUFFER_TILE_SIZE);

    // mul by VIS_TILE_SIZE is not needed, since it'll be normalised
    uvec2 dstCoord = offset + uvec2((quadId & 1) == 0 ? 0 : size.x,
                                    (quadId & 2) == 0 ? 0 : size.y);

    vec2 uv = vec2(dstCoord) / vec2(FINAL_ATLAS_WIDTH, FINAL_ATLAS_HEIGHT);
    gl_Position = vec4(uv * 2 - 1, 0, 1);
}
