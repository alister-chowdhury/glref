#version 460 core

#include "../common.glsli"
#include "../map_atlas_common.glsli"


#define LINE_BVH_V2_STACK_SIZE 9
#define LINE_BVH_V2_BINDING 3
// #include "../../../shaders/grid_based_bvh/v2_tracing.glsli"
#include "../v2_tracing.glsli"


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 

layout(binding=1) uniform sampler2D baseTexture;
layout(binding=2) uniform sampler2D normTexture;
    
layout(location=0) in vec2    uv;
layout(location=0) out vec4   outCol;

layout(location=0) uniform vec2 lightSource;


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
    vec2 lightSourceScaled = lightSource * levelToScreenScale;

    float shadow = 1.0;

#if ENABLE_SHADOW_CASTING
    {
        vec2 targetUV = lightSourceScaled;
        vec2 fromTarget = scaledUv - targetUV;
        float dist = length(fromTarget);
        LineBvhV2Result hit = traceLineBvhV2(targetUV, fromTarget / dist, dist, true);
        if(hit.hit)
        {
            shadow = 0;
        }
    }
#endif // ENABLE_SHADOW_CASTING


    vec3 base = texture(baseTexture, scaledUv).xyz;
    vec4 normAndZ = texture(normTexture, scaledUv);
    vec3 norm = normalize(normAndZ.xyz * 2 - 1);
    float Z = normAndZ.w;
    float maxZLight = 8.0 / 64.0;
    float maxZ = 1.0 / 64.0;
    scaledUv.y -= maxZ * Z;

    vec3 lightSource3D = vec3(lightSourceScaled, maxZLight);
    vec3 source3D = vec3(scaledUv, maxZ * normAndZ.w);
    vec3 dL = lightSource3D - source3D;

    vec3 L = normalize(dL);
    float damp = evaluatePointLightAttenuation(length(dL), 5);
    damp *= 4;
    damp = max(0, min(1, damp));


    outCol = vec4(max(0, min(1, dot(norm, L))) * base * damp * shadow, 1);

    // outCol.xyz = base;
    // outCol.xyz = L;
    // outCol.xyz = vec3(abs(dot(norm, L)));
}
