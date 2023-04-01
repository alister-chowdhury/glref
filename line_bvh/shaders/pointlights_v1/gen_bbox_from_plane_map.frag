#version 460 core

#include "../../../shaders/common.glsl"
#include "pointlights_v1_common.glsli"

layout(binding=0) uniform sampler2D lightPlaneMap;
layout(binding=1) uniform usampler1D lightingData;
layout(location=0) out vec4 outBBox;


#ifndef BIAS_FOR_PCF
#define BIAS_FOR_PCF    1
#endif // BIAS_FOR_PCF

vec2 projectRay(vec3 planeAndDistance, float theta)
{
    vec2 rd = vec2(cos(theta), sin(theta));
    float denom = dot(planeAndDistance.xy, rd);

    // Prevent divisions by zero and excessive expansion at grazing angles
    float onedeg = 0.01745240643728351;
    if(abs(denom) <= onedeg)
    {
        return vec2(0);
    }

    float distToPlane = planeAndDistance.z / denom;
    return rd * distToPlane;
}

void main()
{
    int lineIndex = int(gl_FragCoord.x);

#if FLICKERING_POINT_LIGHTS
    vec2 ro = loadFlickeringPointLightData(lightingData, lineIndex).position;
#else // FLICKERING_POINT_LIGHTS
    vec2 ro = loadPointLightData(lightingData, lineIndex).position;
#endif // FLICKERING_POINT_LIGHTS

    vec2 bboxMax = vec2(-65504.0);
    vec2 bboxMin = vec2(65504.0);

    // Assumed linemap resolution to be a power of 2
    int lightPlaneMapWidth = textureSize(lightPlaneMap, 0).x;
    float invTextureSizeTwoPi = rcpForPowersOf2(float(lightPlaneMapWidth)) * TWOPI;

    for(int x=0; x<lightPlaneMapWidth; ++x)
    {

        vec3 planeAndDistance = texelFetch(lightPlaneMap, ivec2(x, lineIndex), 0).xyz;
             planeAndDistance.xy = planeAndDistance.xy * 2 - 1;

        // Project against the left and right rotational values
        // to prevent underprojecting and not fully containing
        // the light.

#if BIAS_FOR_PCF
        const float bias = 1.0;
#else // BIAS_FOR_PCF
        const float bias = 0.5;
#endif // BIAS_FOR_PCF

        float thetaLeft = (float(x) - bias) * invTextureSizeTwoPi;
        float thetaRight = (float(x) + bias) * invTextureSizeTwoPi;

        vec2 projectionLeft = projectRay(planeAndDistance, thetaLeft);
        vec2 projectionRight = projectRay(planeAndDistance, thetaRight);

        bboxMin = min(min(projectionLeft, projectionRight), bboxMin);
        bboxMax = max(max(projectionLeft, projectionRight), bboxMax);
    }

    outBBox = vec4(bboxMin + ro, bboxMax + ro);
}
