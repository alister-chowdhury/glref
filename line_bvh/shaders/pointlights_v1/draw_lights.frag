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


// layout(location=1) uniform int X0;

#if OUTPUT_CIRCULAR_HARMONICS

layout(location=0) out vec3  outRGBSH0;
layout(location=1) out vec4  outRGBSH1;
layout(location=2) out vec2  outRGBSH2;

#else // OUTPUT_CIRCULAR_HARMONICS

layout(location=0) out vec4 outCol;

#endif // OUTPUT_CIRCULAR_HARMONICS


void main()
{
    float dist = length(localUv);
    vec3 evaluatedColour = evaluatePointLightContrib(dist, colourAndDecayRate.xyz, colourAndDecayRate.w);

    // Apply shadowing via the plane map.
    vec2 planeUV = vec2(getPlaneMapSampleU(localUv, vec2(0)), linemapV);
    vec3 planeAndDistance = texture(lightPlaneMap, planeUV).xyz;
    // planeAndDistance = texelFetch(lightPlaneMap, ivec2(X0 & 511, 0), 0).xyz;
    // vec2 RD = 


    planeAndDistance.xy = planeAndDistance.xy * 2.0 - 1.0;
    evaluatedColour *= getSmoothPlaneVisibility(localUv, planeAndDistance);

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

    outCol = vec4(evaluatedColour, 1.0);

#endif // OUTPUT_CIRCULAR_HARMONICS

}
