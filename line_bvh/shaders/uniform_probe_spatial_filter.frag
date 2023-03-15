#version 460 core

#ifndef PROBE_WIDTH
#define PROBE_WIDTH 4
#endif // PROBE_WIDTH

#ifndef PROBE_HEIGHT
#define PROBE_HEIGHT 4
#endif // PROBE_WIDTH

layout(binding=0) uniform usampler2D    visibilityMask;
layout(binding=1) uniform sampler2D     prefilteredProbeData;

layout(location=0) out vec4 filteredProbeData;


void main()
{

    ivec2 coord = ivec2(gl_FragCoord);
    uint visibilityBits = texelFetch(visibilityMask, coord / ivec2(PROBE_WIDTH, PROBE_HEIGHT), 0).x;

    vec4 sampled = texelFetch(prefilteredProbeData, coord, 0);
    float weight = 1;

    for(int bitIndex=0; bitIndex<8; ++bitIndex)
    {
        if((visibilityBits & (1u << bitIndex)) != 0)
        {
            int adjustedOffset = (bitIndex >= 4) ? (bitIndex + 1) : bitIndex;
            int y = (adjustedOffset / 3) - 1;
            int x = (adjustedOffset % 3) - 1;
            sampled += texelFetch(prefilteredProbeData, coord + ivec2(PROBE_WIDTH, PROBE_HEIGHT) * ivec2(x, y), 0);
            weight += 1.0;
        }
    }

    // Prevent bright spots
    if(weight == 1.0)
    {
        weight = 2.0;
    }

    filteredProbeData = sampled / weight;
}
