#version 460 core

#include "../../shaders/common.glsl"

#ifndef TRACE_METHOD
#define TRACE_METHOD 0
#endif // TRACE_METHOD


#if TRACE_METHOD == 0
#include "df_tracing.glsli"
#else // TRACE_METHOD == 1
#include "v1_tracing.glsli"
#endif // TRACE_METHOD

layout(location=0) in vec2 uv;
layout(location=0) out uvec4 outDistances;


uint traceDistanceForU8(float index)
{
    // TODO: Add golden ratio jitter based upon the probe index
    float probeAngle = index / 16.0 * TWOPI;
    vec2 probeDir = vec2(cos(probeAngle), sin(probeAngle));

#if TRACE_METHOD == 0
    float dist = df_trace(uv, probeDir, 2.0).finalDist;
#else
    float dist = sqrt(traceLineBvhV1(uv, probeDir, 2.0, false).hitDistSq);
#endif

    // No hit
    if(dist > 1.0)
    {
        dist = 0.0;
    }

    // TODO: Should really bias this, so it returns just before a wall.
    //       should also set to 0 if we'd be sampling the same probe (no self propagation).

    return uint(dist * 255); // implicit round down
}

uint packU8ToU32(uint a, uint b, uint c, uint d)
{
    return a | (b << 8) | (c << 16) | (d << 24);
}


void main()
{
    uint distance00 = traceDistanceForU8(0.0);
    uint distance01 = traceDistanceForU8(1.0);
    uint distance02 = traceDistanceForU8(2.0);
    uint distance03 = traceDistanceForU8(3.0);
    uint distance04 = traceDistanceForU8(4.0);
    uint distance05 = traceDistanceForU8(5.0);
    uint distance06 = traceDistanceForU8(6.0);
    uint distance07 = traceDistanceForU8(7.0);
    uint distance08 = traceDistanceForU8(8.0);
    uint distance09 = traceDistanceForU8(9.0);
    uint distance10 = traceDistanceForU8(10.0);
    uint distance11 = traceDistanceForU8(11.0);
    uint distance12 = traceDistanceForU8(12.0);
    uint distance13 = traceDistanceForU8(13.0);
    uint distance14 = traceDistanceForU8(14.0);
    uint distance15 = traceDistanceForU8(15.0);

    uvec4 distances = uvec4(
        packU8ToU32(distance00, distance01, distance02, distance03),
        packU8ToU32(distance04, distance05, distance06, distance07),
        packU8ToU32(distance08, distance09, distance10, distance11),
        packU8ToU32(distance12, distance13, distance14, distance15)
    );

    outDistances = distances;
}
