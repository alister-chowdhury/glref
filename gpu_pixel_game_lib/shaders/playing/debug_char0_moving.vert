#version 460 core


#define GLOBAL_PARAMETERS_BINDING       0
#define ASSET_ATLAS_BINDING             1
#include "../common.glsli"
#include "../bindings.glsli"
#include "../map_atlas_common.glsli"
#include "../pathfinding_common.glsli"
#include "../../assets/ASSET_ATLAS.glsl"

layout(set=0, binding = 2) uniform playerPos_
{
    vec2 playerPos;
};

layout(set=0, binding = 3) uniform playerDir_
{
    vec2 playerDir;
};

layout(location=0) uniform float time;


layout(location=0) out vec2 uv;

void main()
{
    int quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);

    // harcoded for now, for a lack of a anim data system
    bool flipX = false;
    float animSpeed = 1.0;
    uint animBaseId = 0u;
    uint frameMask = 3;
    if(abs(playerDir.x) > abs(playerDir.y))
    {
        animSpeed *= 0.5;
        animBaseId = ASSET_ATLAS_ID_CHAR0_WALK_RGT0;
        flipX = playerDir.x < 0;
        frameMask = 1;
    }
    else
    {
        animBaseId = (playerDir.y > 0) ? ASSET_ATLAS_ID_CHAR0_WALK_BCK0 : ASSET_ATLAS_ID_CHAR0_WALK_FWD0;
    }


    uint assetId = animBaseId + (uint(floor(time * animSpeed)) & frameMask);
    AssetAtlasInfo assetAtlasInfo = loadAssetAtlasInfo(assetId, assetAtlasBuffer);

    if(flipX)
    {
        assetAtlasInfo.atlasUvRegion.xz = assetAtlasInfo.atlasUvRegion.zx;
        assetAtlasInfo.rectPadding.xz = assetAtlasInfo.rectPadding.zx;
    }

    uv = vec2((quadId & 1) == 0 ? assetAtlasInfo.atlasUvRegion.x : assetAtlasInfo.atlasUvRegion.z,
              (quadId & 2) == 0 ? assetAtlasInfo.atlasUvRegion.w : assetAtlasInfo.atlasUvRegion.y)
             ;

    vec2 ndc = vec2((quadId & 1) == 0 ? (assetAtlasInfo.roi.x/16.0) : (assetAtlasInfo.roi.z/16.0),
                    (quadId & 2) == 0 ? (assetAtlasInfo.roi.y/16.0) : (assetAtlasInfo.roi.w/16.0));

    // vec2 ndc = vec2((quadId & 1) == 0 ? 0 : 1,
    //                 (quadId & 2) == 0 ? 0 : 1);

    ndc.x -= 0.5;
    // ndc.y += 1.0;

    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);
    
    float levelToScreenScale = getBackgroundToLevelScale(atlasInfo);
    float backgroundToLevelScale = getBackgroundToLevelScale(atlasInfo);

    ndc = ndc * levelToScreenScale * (1.0 / 64.0)
        + backgroundToLevelScale * playerPos
        ;

    gl_Position = vec4(ndc * 2 - 1, 0, 1);
}
