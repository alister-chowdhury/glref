#version 460 core


#define GLOBAL_PARAMETERS_BINDING       0
#include "../common.glsli"
#include "../bindings.glsli"
#include "../map_atlas_common.glsli"
#include "../pathfinding_common.glsli"

layout(set=0, binding = 1) uniform playerPos_
{
    vec2 playerPos;
};

layout(set=0, binding = 2) uniform playerDir_
{
    vec2 playerDir;
};

layout(location=0) out vec2 outShapeNdc;

void main()
{
    int quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);
    vec2 ndc = vec2((quadId & 1) == 0 ? -1.0 : 1.0,
                    (quadId & 2) == 0 ? -1.0 : 1.0);
    outShapeNdc = ndc;

    ndc.y *= 0.5;
    ndc.x += 1.0/3.0;

    ndc = vec2(dot(playerDir, ndc),
               dot(vec2(playerDir.y, -playerDir.x), ndc));

    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);
    
    float levelToScreenScale = getBackgroundToLevelScale(atlasInfo);
    float backgroundToLevelScale = getBackgroundToLevelScale(atlasInfo);

    ndc = ndc * levelToScreenScale * (1.0 / 64.0)
        + backgroundToLevelScale * playerPos * 2 - 1
        ;

    gl_Position = vec4(ndc, 0, 1);
}
