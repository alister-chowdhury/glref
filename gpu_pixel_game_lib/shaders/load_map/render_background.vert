#version 460 core

// dispatch GL_TRIANGLES, 64*64*6

#define ASSET_ATLAS_TILE_VARIANTS   8


#include "../common.glsli"
#include "../map_atlas_common.glsli"
#include "../../assets/ASSET_ATLAS.glsl"

layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 

readonly layout(binding=1, r32ui)    uniform uimage2D mapAtlas;
readonly layout(binding=2)           buffer assetAtlasBuffer_ { uvec4 assetAtlasBuffer[];};

layout(location=0) out vec3 pixelCoordAndHeight;
layout(location=1) out vec2 uv;

bool sampleCoord(ivec2 localCoord, MapAtlasLevelInfo atlasInfo)
{
    if(localCoord.x < atlasInfo.size.x
        && localCoord.x >= 0
        && localCoord.y < atlasInfo.size.y
        && localCoord.y >= 0)
    {
        ivec2 coord = localCoord + ivec2(atlasInfo.offset);
        return hasAnySectors(imageLoad(mapAtlas, coord).x);
    }
    return false;
}


void main()
{
    int pixelId = gl_VertexID / 6;
    ivec2 levelCoord = ivec2(pixelId % BACKGROUND_TILE_DIM,
                             pixelId / BACKGROUND_TILE_DIM);
    int vertexId = triangleToQuadVertexIdZ(gl_VertexID % 6);
    vec2 localUv = vec2((vertexId & 1), (vertexId >> 1));
    uv = (vec2(levelCoord) + localUv) * (1.0 / BACKGROUND_TILE_DIM);
    gl_Position = vec4(uv * 2.0 - 1.0,
                       0.0,
                       1.0);

    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);

    uint assetId = ASSET_ATLAS_ID_EMPTY;
    vec2 heights = vec2(0.0);

    if((levelCoord.x < atlasInfo.size.x) && (levelCoord.y < atlasInfo.size.y))
    {
        bool cellVisible = sampleCoord(levelCoord, atlasInfo);    
        if(cellVisible)
        {
            assetId = ASSET_ATLAS_ID_GROUND_L00_V0;
        }
        else
        {
            assetId = ASSET_ATLAS_ID_BRICKS_L00_V0;

            if(sampleCoord(levelCoord - ivec2(0, 1), atlasInfo))
            {
                heights.y = 1.0;
            }
            else
            {
                // This is a hack to blend wall corners
                // it makes no sense whatsoever, if it breaks
                // stuff, just disable this branch
                if(sampleCoord(levelCoord - ivec2(0, 2), atlasInfo))
                {
                    heights.x = 0.5;
                }
            }
        }

        // Effectively:
        // shuffle([variant0 ... variantN]) every N tiles.
        //
        // This helps hide repeating patterns.
        uint localShift = simpleHash32(uvec3(
            uint(levelCoord.y) + uint(levelCoord.x / ASSET_ATLAS_TILE_VARIANTS),
            globals.levelGenSeed,
            level
        ));
        assetId = assetId
                + level * ASSET_ATLAS_TILE_VARIANTS
                + (localShift ^ levelCoord.x) % ASSET_ATLAS_TILE_VARIANTS;

    }

    AssetAtlasInfo assetAtlasInfo = loadAssetAtlasInfo(assetId, assetAtlasBuffer);
    pixelCoordAndHeight = vec3(
        (vertexId & 1) == 0 ? assetAtlasInfo.atlasPixelRegion.x :assetAtlasInfo.atlasPixelRegion.z,
        (vertexId & 2) == 0 ? assetAtlasInfo.atlasPixelRegion.y :assetAtlasInfo.atlasPixelRegion.w,
        (vertexId & 2) == 0 ? heights.x : heights.y
    );
}
