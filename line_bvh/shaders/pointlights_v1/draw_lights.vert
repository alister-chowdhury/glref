#version 460 core

#include "../../../shaders/common.glsl"
#include "pointlights_v1_common.glsli"

layout(binding=0) uniform usampler1D lightingData;

#if USE_OBBOX
layout(binding=2) uniform usampler1D lightOBBox;
#else // USE_OBBOX
layout(binding=2) uniform sampler1D lightBBox;
#endif // USE_OBBOX

layout(location=0) uniform float invNumLights;


layout(location=0) out vec2 localUv;
flat layout(location=1) out float linemapV;
flat layout(location=2) out vec4 colourAndDecayRate;


void main()
{
    int lightIndex = int(gl_VertexID) / 6;
    int quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);

#if USE_OBBOX
    uvec4 obbox = texelFetch(lightOBBox, lightIndex, 0);
    vec2 uv;
    switch(quadId)
    {
        case 0: uv = unpackHalf2x16(obbox.x); break;
        case 1: uv = unpackHalf2x16(obbox.y); break;
        case 2: uv = unpackHalf2x16(obbox.w); break;
        case 3: uv = unpackHalf2x16(obbox.z); break;
    }
#else // USE_OBBOX
    vec4 bbox = texelFetch(lightBBox, lightIndex, 0);
    vec2 uv = vec2(
        ((quadId & 1) == 0) ? bbox.x : bbox.z,
        ((quadId & 2) == 0) ? bbox.y : bbox.w
    );
#endif // USE_OBBOX

    gl_Position = vec4(uv * 2 - 1, 0., 1.);

#if FLICKERING_POINT_LIGHTS
    FlickeringPointLightData flickeringPointLightData = loadFlickeringPointLightData(lightingData, lightIndex);
    float time = 0.0; // todo
    PointLightData pointLightData = collapseFlickeringPointLightData(flickeringPointLightData, time);
#else // FLICKERING_POINT_LIGHTS
    PointLightData pointLightData = loadPointLightData(lightingData, lightIndex);
#endif // FLICKERING_POINT_LIGHTS

    localUv = uv - pointLightData.position;
    linemapV = (float(lightIndex) + 0.5) * invNumLights;
    colourAndDecayRate = vec4(pointLightData.colour, pointLightData.decayRate);
}
