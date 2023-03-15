#version 460 core

#include "df_tracing.glsli"


layout(location=1)  uniform vec2 invProbeTextureSize; 
layout(location=0) in vec2 uv;
layout(location=0) out uint outVisMask;


void main()
{

    uint mask = 0;

    // Bit pattern:
    // 0 1 2
    // 3   4
    // 5 6 7
    for(int bitIndex=0; bitIndex<8; ++bitIndex)
    {
        int adjustedOffset = (bitIndex >= 4) ? (bitIndex + 1) : bitIndex;
        int y = (adjustedOffset / 3) - 1;
        int x = (adjustedOffset % 3) - 1;

        vec2 rd = vec2(x, y) * invProbeTextureSize;
        vec2 cmpUv = uv + rd;
        if(cmpUv.x > 0 && cmpUv.y > 0 && cmpUv.x < 1 && cmpUv.y < 1)
        {
            float rdlen = length(rd);
            rd /= rdlen;
            if(df_trace(uv, rd, rdlen).visible)
            {
                mask |= (1u << bitIndex);
            }
        }
    }

    outVisMask = mask;
}
