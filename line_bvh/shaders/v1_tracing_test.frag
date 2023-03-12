#version 460 core

#include "v1_tracing.glsli"

layout(location=0)  uniform vec2 targetUV;
layout(location=0) in vec2 uv;
layout(location=0) out vec4 col;

uint wang_hash(uint seed)
{
    seed = (seed ^ 61) ^ (seed >> 16);
    seed *= 9;
    seed = seed ^ (seed >> 4);
    seed *= 0x27d4eb2d;
    seed = seed ^ (seed >> 15);
    return seed;
}


vec3 hs1(float H)
{
    float R = abs(H * 6 - 3) - 1;
    float G = 2 - abs(H * 6 - 2);
    float B = 2 - abs(H * 6 - 4);
    return clamp(vec3(R,G,B), vec3(0), vec3(1));
}


vec3 randomHs1Col(uint idx)
{
    return hs1((wang_hash(idx) & 0xffff) / 65535.0);
}

void main()
{

    bool stopOnFirstHit = true;

    // Trace from UV to target
#if 0
    vec2 toTarget = targetUV - uv;
    float dist = length(toTarget);
    LineBvhV1Result hit = traceLineBvhV1(uv, toTarget / dist, dist, stopOnFirstHit);

    // Trace from target to UV
#else
    vec2 fromTarget = uv - targetUV;
    float dist = length(fromTarget);
    LineBvhV1Result hit = traceLineBvhV1(targetUV, fromTarget / dist, dist, stopOnFirstHit);
#endif

    float numVisits = float(hit.numNodesVisited) / 16.0;
    float numIntersections = float(hit.numLineIntersections) / 16.0;
    float noHit = float(hit.hitLineId == 0xffffffffu);
    col = vec4(numVisits, numIntersections, noHit, 1.);
    // col = vec4(randomHs1Col(hit.hitLineId),1);

}

