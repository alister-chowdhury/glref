#version 460 core

#define GLOBAL_PARAMETERS_BINDING       0
#include "../common.glsli"
#include "../bindings.glsli"
#include "../map_atlas_common.glsli"
#include "../ch_common.glsli"

layout(set=0, binding = 1) uniform playerPos_
{
    vec2 playerPos;
};

layout(binding=2) uniform sampler2D baseTexture;
layout(binding=3) uniform sampler2D normTexture;
layout(binding=4) uniform sampler2D visibilityTexture;
layout(binding=5) uniform sampler2D directLightingV0;
layout(binding=6) uniform sampler2D directLightingV1;
layout(binding=7) uniform sampler2D directLightingV2;
layout(binding=8) uniform sampler2D visHistoryTexture;
    
layout(location=0) in vec2    uv;
layout(location=0) out vec4   outCol;


float evaluatePointLightAttenuation(float dist, float decayRate)
{
    return pow(dist + 1, -decayRate);
}

void main()
{

    uint level = globals.currentLevel;
    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);
    float levelToScreenScale = getLevelToBackgroundScale(atlasInfo);

    vec2 scaledUv = uv * levelToScreenScale;
    float shadow = texture(visibilityTexture, scaledUv).x;
    float shadowHistory = texture(visHistoryTexture, levelUVToAtlasUV(uv, atlasInfo)).x;

    vec3 base = texture(baseTexture, scaledUv).xyz;
    vec4 normAndZ = texture(normTexture, scaledUv);
    vec3 norm = normalize(normAndZ.xyz * 2 - 1);
    float Z = normAndZ.w;
    float maxZLight = 8.0 / 64.0;
    float maxZ = 1.0 / 64.0;

    // Scene lighting
    PackedRGBCH2 packedRGB;
    packedRGB.V0 = texture(directLightingV0, scaledUv).xyz;
    packedRGB.V1 = texture(directLightingV1, scaledUv).xyzw;
    packedRGB.V2 = texture(directLightingV2, scaledUv).xy;
    CH2 R, G, B;
    unpackRGBCH2(packedRGB, R, G, B);
    CH2 directCH = CH2LambertianRadianceBasis(norm.xy * (Z * 0.9 + 0.1));
    vec3 directLight = vec3(CH2Dot(directCH, R),
                            CH2Dot(directCH, G),
                            CH2Dot(directCH, B));

    scaledUv.y -= maxZ * Z;

    vec3 playerPos3D = vec3(playerPos, maxZLight);
    vec3 source3D = vec3(scaledUv, maxZ * normAndZ.w);
    vec3 dL = playerPos3D - source3D;

    vec3 L = normalize(dL);
    float damp = evaluatePointLightAttenuation(length(dL), 5);
    damp = max(0, min(1, damp));
    float visLighting = max(0, min(1, dot(norm, L))) * damp;

    outCol = vec4((directLight * shadowHistory + visLighting * shadow) * base, 1);
}
