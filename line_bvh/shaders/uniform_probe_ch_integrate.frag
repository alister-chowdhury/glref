#version 460 core

#include "../../shaders/common.glsl"
#include "ch_common.glsli"


#ifndef PROBE_WIDTH
#define PROBE_WIDTH 4
#endif // PROBE_WIDTH

#ifndef PROBE_HEIGHT
#define PROBE_HEIGHT 4
#endif // PROBE_WIDTH


layout(binding=0) uniform sampler2D sceneSamples;

layout(location=0) out vec3  OutRGBSH0;
layout(location=1) out vec4  OutRGBSH1;
layout(location=2) out vec2  OutRGBSH2;


void main()
{

    ivec2 sampleCoordStart = ivec2(gl_FragCoord) * ivec2(PROBE_WIDTH, PROBE_HEIGHT);

    CH2 accumR;
    CH2 accumG;
    CH2 accumB;

    for(int i=0; i<(PROBE_WIDTH*PROBE_HEIGHT); ++i)
    {
        float probeAngle = float(i) / float(PROBE_WIDTH * PROBE_HEIGHT) * TWOPI;
        vec2 probeDir = vec2(cos(probeAngle), sin(probeAngle));
        
        int probeTraceX = i % PROBE_WIDTH;
        int probeTraceY = i / PROBE_WIDTH;

#if ACCUMULATE_RADIANCE
        CH2 probeBasis = CH2LambertianRadianceBasis(probeDir);
#else // ACCUMULATE_RADIANCE
        CH2 probeBasis = CH2Basis(probeDir);
#endif // ACCUMULATE_RADIANCE
        
        probeBasis.V *= 1.0 / (PROBE_WIDTH * PROBE_HEIGHT);
        
        vec3 sampled = texelFetch(sceneSamples, sampleCoordStart + ivec2(probeTraceX, probeTraceY), 0).xyz;
        
        accumR = CH2Add(accumR, CH2Mul(probeBasis, sampled.x));
        accumG = CH2Add(accumG, CH2Mul(probeBasis, sampled.y));
        accumB = CH2Add(accumB, CH2Mul(probeBasis, sampled.z));
    }

    OutRGBSH0 = vec3(accumR.V.x, accumG.V.x, accumB.V.x);
    OutRGBSH1 = vec4(accumR.V.yz, accumG.V.yz);
    OutRGBSH2 = accumB.V.yz;
}
