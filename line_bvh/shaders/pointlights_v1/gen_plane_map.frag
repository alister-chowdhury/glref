#version 460 core

#include "../../../shaders/common.glsl"
#include "../v1_tracing.glsli"
#include "pointlights_v1_common.glsli"

layout(binding=1) uniform usampler1D lightingData;

layout(location=0) in vec2 uv;
layout(location=0) out vec4 outPlane;


void main()
{

#if FLICKERING_POINT_LIGHTS
    vec2 ro = loadFlickeringPointLightData(lightingData, int(gl_FragCoord.y)).position;
#else // FLICKERING_POINT_LIGHTS
    vec2 ro = loadPointLightData(lightingData, int(gl_FragCoord.y)).position;
#endif // FLICKERING_POINT_LIGHTS

    vec2 rd = vec2(cos(uv.x * TWOPI), sin(uv.x * TWOPI));
    LineBvhV1Result hit = traceLineBvhV1(ro, rd, 1.0, false);

    vec2 N = rd;
    float w = 1.0;

    if(hit.hitLineId != 0xffffffffu)
    {
        N = normalize(vec2(hit.line.w, -hit.line.z));
        w = dot(N, hit.line.xy - ro);
        // Ensure a consistent clockwise orientation plus
        // keep the distance coef positive.
        // N.x = multiplySign(N.x, w);
        // N.y = multiplySign(N.y, w);
        // // w = multiplySign(w, w);
        // w = dot(N, hit.line.xy - ro);
    }

    // R10G10B10A2 encoding, A2 is currently unused...
    outPlane = vec4(N * 0.5 + 0.5, w, 1.0);
}
