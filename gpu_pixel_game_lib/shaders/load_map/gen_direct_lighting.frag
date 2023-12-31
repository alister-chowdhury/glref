#version 460 core

#include "../common.glsli"
#include "../map_atlas_common.glsli"
#include "../ch_common.glsli"

#define LINE_BVH_V2_STACK_SIZE 9
#define LINE_BVH_V2_BINDING 2
#include "../v2_tracing.glsli"


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 

readonly layout(std430, binding = 1) buffer mapAtlasData_ { uint mapAtlasData[]; };

layout(location=0) in vec2  uv;

layout(location=0) out vec3   outV0;
layout(location=1) out vec4   outV1;
layout(location=2) out vec2   outV2;


// Uses the last 23bits to construct a linear range
// [0, 1) = [0.25, 0.75)
float randomBounded05(uint seed)
{
    // 1x shift_add
    // 1x add
    seed = 0x3f000000u + (seed & 0x7fffffu);
    return uintBitsToFloat(seed) - 0.25f;
}

// Uses the last 23bits to construct a linear range
// [0, 1) = [0.5, 1)
float randomBounded0505(uint seed)
{
    // 1x shift_add
    // 1x add
    seed = 0x3f000000u + (seed & 0x7fffffu);
    return uintBitsToFloat(seed);
}

float evaluatePointLightAttenuation(float dist, float decayRate)
{
    return pow(dist + 1, -decayRate);
}


void main()
{
    CH2 R = CHZero();
    CH2 G = CHZero();
    CH2 B = CHZero();

    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);

    ivec2 localCoord = ivec2(uv * BACKGROUND_TILE_DIM);
    if((localCoord.x < atlasInfo.size.x) && (localCoord.y < atlasInfo.size.y))
    {
        uint levelDataOffset = level * MAP_ATLAS_LEVEL_DATA_STRIDE;
        uint roomSpanOffset = levelDataOffset + MAP_ATLAS_LEVEL_DATA_ROOM_SPANS_OFFSET;
        uint numRooms = mapAtlasData[levelDataOffset + MAP_ATLAS_LEVEL_DATA_NUM_ROOMS_OFFSET];
        for(uint room = 0u; room < numRooms; ++room)
        {
            ivec4 roomSpan = unpackSpan(mapAtlasData[roomSpanOffset + room]);
            vec4 roomSpanUV = vec4(roomSpan) * (1.0 / BACKGROUND_TILE_DIM);

            // todo, add jitter / variation etc
            uint seed0 = simpleHash32(uvec3(globals.levelGenSeed, level, room));
            uint seed1 = simpleHash32(uvec3(seed0, globals.levelGenSeed, room));
            uint seed2 = simpleHash32(uvec3(seed1, seed0, room));
            uint seed3 = simpleHash32(uvec3(seed2, seed1, seed0));

            vec2 pointLightUV = vec2(
                mix(roomSpanUV.x, roomSpanUV.z, randomBounded05(seed0)),
                mix(roomSpanUV.y, roomSpanUV.w, randomBounded05(seed1))
            );
            float decayRate = mix(10, 15, randomBounded(seed2));
            vec3 pointLightCol = hs1(randomBounded0505(seed3));
                 pointLightCol = mix(pointLightCol, vec3(1), 0.3);

            vec2 toPointLight = pointLightUV - uv;
            float dist = length(toPointLight);
            vec2 toPointLightN = toPointLight / dist;

            LineBvhV2Result hit = traceLineBvhV2(pointLightUV,
                                                 -toPointLightN,
                                                 dist,
                                                 true);

            if(!hit.hit)
            {
                float damp = evaluatePointLightAttenuation(dist, decayRate);
                damp = max(0, min(1, damp));

                CH2AccumPointLight(toPointLightN,
                                   pointLightCol * damp,
                                   R, G, B);
            }
        }
    }

    const float boost = 8;
    PackedRGBCH2 packed = packRGBCH2(R, G, B);
    outV0 = packed.V0 * boost;
    outV1 = packed.V1 * boost;
    outV2 = packed.V2 * boost;
}
