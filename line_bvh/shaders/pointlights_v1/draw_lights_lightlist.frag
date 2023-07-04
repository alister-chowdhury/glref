#version 460 core

#error "THIS IS SUPER BROKEN, DO NOT USE"

#include "../../../shaders/common.glsl"


#include "pointlights_v1_common.glsli"

layout(binding=0) uniform usampler1D lightingData;
layout(binding=1) uniform sampler2D lightPlaneMap;
layout(binding=2) uniform usampler2D lightList;


layout(location=0) uniform uvec3 lightListInfo; // .xy = tileSize
                                                // .y = pixelWidth [(numLights + 127) / 128]
layout(location=1) uniform float invNumLights;

layout(location=0) in vec2 uv;
layout(location=0) out vec4 outCol;


// only PLANE_BLOCKING_MODE_BINARY_LINEAR and
//      PLANE_BLOCKING_MODE_SMOOTH_LINEAR and   <--- maybe not?
//      PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF
//      please 

#define PLANE_BLOCKING_MODE_SMOOTH_LINEAR       0
#define PLANE_BLOCKING_MODE_BINARY_LINEAR       1
#define PLANE_BLOCKING_MODE_BINARY_TWOTAP       2
#define PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF   3

#ifndef PLANE_BLOCKING_MODE
#define PLANE_BLOCKING_MODE PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF
#endif // PLANE_BLOCKING_MODE



void accumLights(uint baseLightId, uint masks, vec2 pixelUV, inout vec3 accum)
{
    while(masks != 0)
    {
        uint index = findLSB(masks);
        masks -= (1u << index);
        int lightIndex = int(baseLightId + index);

#if FLICKERING_POINT_LIGHTS
        FlickeringPointLightData flickeringPointLightData = loadFlickeringPointLightData(lightingData, lightIndex);
        float time = 0.0; // todo
        PointLightData pointLightData = collapseFlickeringPointLightData(flickeringPointLightData, time);
#else // FLICKERING_POINT_LIGHTS
        PointLightData pointLightData = loadPointLightData(lightingData, lightIndex);
#endif // FLICKERING_POINT_LIGHTS

        vec2 localUv = pixelUV - pointLightData.position;
        float linemapV = (float(lightIndex) + 0.5) * invNumLights;        
        vec4 colourAndDecayRate = vec4(pointLightData.colour, pointLightData.decayRate);

        float dist = length(localUv);
        vec3 evaluatedColour = evaluatePointLightContrib(dist, colourAndDecayRate.xyz, colourAndDecayRate.w);
        vec2 planeUV = vec2(getPlaneMapSampleU(localUv, vec2(0)), linemapV);

    // Apply shadowing via the plane map.
#if (PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_SMOOTH_LINEAR) || (PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_LINEAR)

        vec3 planeAndDistance = texture(lightPlaneMap, planeUV).xyz;
        planeAndDistance.xy = planeAndDistance.xy * 2.0 - 1.0;
   
#   if PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_SMOOTH_LINEAR 

        // Artefacts at plane transitions (which is what it is attempting to avoid)
        evaluatedColour *= getSmoothPlaneVisibility(localUv, planeAndDistance);


#   else // PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_LINEAR
    
        // Sometimes has horribly blobbing artefacts 
        evaluatedColour *= getBinaryPlaneVisibility(localUv, planeAndDistance);

#   endif // PLANE_BLOCKING_MODE

#else // PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_TWOTAP || PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF

        // Two taps and two binary plane tests, texture width is assumed to be a power of 2,
        // more expensive, but generally just looks better.
        
        planeUV.x = fract(planeUV.x);

        ivec2 mapSize = textureSize(lightPlaneMap, 0);
        float sampleXBase = planeUV.x * mapSize.x - 0.5;
        int sampleY = int(planeUV.y * mapSize.y);
        int sampleX0 = int(sampleXBase);
        int sampleX1 = sampleX0 + 1;
        sampleX0 &= (mapSize.x - 1);
        sampleX1 &= (mapSize.x - 1);
        vec3 planeAndDistance0 = texelFetch(lightPlaneMap, ivec2(sampleX0, sampleY), 0).xyz;
        vec3 planeAndDistance1 = texelFetch(lightPlaneMap, ivec2(sampleX1, sampleY), 0).xyz;
        planeAndDistance0.xy = planeAndDistance0.xy * 2.0 - 1.0;
        planeAndDistance1.xy = planeAndDistance1.xy * 2.0 - 1.0;

        float visbility0 = getBinaryPlaneVisibility(localUv, planeAndDistance0);
        float visbility1 = getBinaryPlaneVisibility(localUv, planeAndDistance1);

#if PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF
        float lerpWeight = fract(sampleXBase);
              lerpWeight = smoothstep(0, 1, lerpWeight);
        float visbility = mix(visbility0, visbility1, lerpWeight);
#else // PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF
        float visbility = visbility0 * visbility1;
#endif // PLANE_BLOCKING_MODE == PLANE_BLOCKING_MODE_BINARY_TWOTAP_PCF

        evaluatedColour *= visbility;

#endif // PLANE_BLOCKING_MODE

        accum += evaluatedColour;
    }
}

void main()
{
    uvec2 pixel = uvec2(gl_FragCoord.xy);
    uvec2 lightListStart = pixel / lightListInfo.xy;
          lightListStart.x *= lightListInfo.z;
    uint lightListEnd = lightListStart.x + lightListInfo.z;

    vec3 accum = vec3(0);

    uint baseLightId = 0;
    for(; lightListStart.x < lightListEnd; ++lightListStart.x)
    {
        uvec4 masks = texelFetch(lightList, ivec2(lightListStart), 0);
        accumLights(baseLightId, masks.x, uv, accum); baseLightId += 32;
        accumLights(baseLightId, masks.y, uv, accum); baseLightId += 32;
        accumLights(baseLightId, masks.z, uv, accum); baseLightId += 32;
        accumLights(baseLightId, masks.w, uv, accum); baseLightId += 32;
    }

    outCol = vec4(accum, 0.0);
}
