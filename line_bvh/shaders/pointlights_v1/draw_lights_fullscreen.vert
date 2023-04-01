#version 460 core

#include "../../../shaders/common.glsl"
#include "pointlights_v1_common.glsli"

layout(binding=0) uniform usampler1D lightingData;
layout(location=0) uniform float invNumLights;


layout(location=0) out vec2 localUv;
flat layout(location=1) out float linemapV;
flat layout(location=2) out vec4 colourAndDecayRate;


void main()
{
    int lightIndex = int(gl_VertexID) / 3;
    int vertexId = int(gl_VertexID) % 3;

    vec2 ndc = vec2(
        vertexId == 0 ? -4 : 1,
        vertexId == 2 ? 4 : -1
    );
    gl_Position = vec4(ndc, 0., 1.);

    vec2 uv = ndc * 0.5 + 0.5;

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
