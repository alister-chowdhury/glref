#version 460 core

#include "df_tracing.glsli"


layout(location=1)  uniform vec2 targetUV;
layout(location=0) in vec2 uv;
layout(location=0) out vec4 col;


void main()
{

    // Trace from UV to target
#if 0
    vec2 toTarget = targetUV - uv;
    float dist = length(toTarget);
    vec2 ro = uv;
    vec2 rd = toTarget / dist;
    // Trace from target to UV
#else
    vec2 fromTarget = uv - targetUV;
    float dist = length(fromTarget);
    vec2 ro = targetUV;
    vec2 rd = fromTarget / dist;
#endif

    DFTraceResult result = df_trace(ro, rd, dist);

    float numVisits = float(result.numSamples) / float(64);
    float noHit = float(result.visible);
    float mipF = result.finalMip / 6.0;
    // col = vec4(numVisits, noHit, mipF, 1.);
    // col = vec4(noHit, mipF, mipF, 1);
    col = vec4(noHit, noHit, noHit, 1);
}
