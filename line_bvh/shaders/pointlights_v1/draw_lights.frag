#version 460 core

#include "../../../shaders/common.glsl"

#if OUTPUT_CIRCULAR_HARMONICS
#include "../ch_common.glsli"
#endif // OUTPUT_CIRCULAR_HARMONICS

#include "pointlights_v1_common.glsli"

layout(binding=1) uniform sampler2D lightPlaneMap;

layout(location=0) in vec2 localUv;
flat layout(location=1) in float linemapV;
flat layout(location=2) in vec4 colourAndDecayRate;

#if OUTPUT_CIRCULAR_HARMONICS

layout(location=0) out vec3  outRGBSH0;
layout(location=1) out vec4  outRGBSH1;
layout(location=2) out vec2  outRGBSH2;

#else // OUTPUT_CIRCULAR_HARMONICS

layout(location=0) out vec4 outCol;

#endif // OUTPUT_CIRCULAR_HARMONICS



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


void main()
{
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


#if OUTPUT_CIRCULAR_HARMONICS

    vec2 N = localUv;
    if(dist != 0.0)
    {
        N /= dist;
    }

    CH2 Basis = CH2DirectLightRadiance(N);
    PackedRGBCH2 outputs = packRGBCH2(CH2Mul(Basis, evaluatedColour.x),
                                      CH2Mul(Basis, evaluatedColour.y),
                                      CH2Mul(Basis, evaluatedColour.z));
    outRGBSH0 = outputs.V0;
    outRGBSH1 = outputs.V1;
    outRGBSH2 = outputs.V2;

#else // OUTPUT_CIRCULAR_HARMONICS

    outCol = vec4(evaluatedColour, 0.0);

#endif // OUTPUT_CIRCULAR_HARMONICS

}
