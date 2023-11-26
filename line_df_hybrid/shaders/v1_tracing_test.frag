#version 460 core

#include "v1_df_rtrace_hybrid.glsli"

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


    // Trace from UV to target
#if 0
    vec2 toTarget = targetUV - uv;
    float dist = length(toTarget);
    TraceHybridV1Result hit = traceHybridV1(uv, toTarget / dist, dist);

    // Trace from target to UV
#else
    vec2 fromTarget = uv - targetUV;
    float dist = length(fromTarget);
    TraceHybridV1Result hit = traceHybridV1(targetUV, fromTarget / dist, dist);
#endif

    float numVisits = float(hit.numIterations) / 16.0;
    float numIntersections = float(hit.numLineIntersections) / 3.0;
    float noHit = float(!hit.hit);
    col = vec4(numVisits, numIntersections, noHit, 1.);
    // col = vec4(randomHs1Col(hit.hitLineId),1);

    col = vec4(noHit);
    // col = vec4(numVisits);
    // col = vec4(numIntersections, noHit, noHit, 0);
    // col = vec4(numIntersections);


    if(false)
    {
        ivec2 coord = ivec2(uv * v1HybridParams.xx + 0.5);
        uint texelData = texelFetch(v1DfTexture, coord, 0).x;
        float testDist = float(texelData & 0xff) / 255.0;
        uint numLines = (texelData >> 8) & 0xff;
        uint offset = (texelData >> 16);
        col = vec4(testDist*10,  float(numLines)/2., float(offset)/300.0, 0.).zzzz;
    }

    if(false)
    {
        ivec2 coord = ivec2(uv * v1HybridParams.xx + 0.5);
        col.xyz = randomHs1Col(uint(coord.x * 1000 + coord.y));
    }
}

