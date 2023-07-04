#version 460 core

#include "../../../shaders/common.glsl"
#include "pointlights_v1_common.glsli"


layout(location=0) uniform uvec2 lightInfo; // .x = numLights
                                            // .y = pixelWidth [(numLights + 127) / 128]

layout(location=1) uniform vec4 tileInfo;   // .xy = scale      (2.0 / tileSize)
                                            // .zw = offset     (-1.0)

#if USE_OBBOX
layout(binding=0) uniform usampler1D lightOBBox;
#else // USE_OBBOX
layout(binding=0) uniform sampler1D lightBBox;
#endif // USE_OBBOX


layout(location=0) out uvec4 outBitMask;


uint evaluateRange(uint start, uint end, vec4 bounds)
{
    uint mask = 0;
    uint index = 0;
    for(; start < end; ++start, ++index)
    {
#if USE_OBBOX

        uvec4 obbox = texelFetch(lightOBBox, int(start), 0);
        vec2 A = unpackHalf2x16(obbox.x);
        vec2 B = unpackHalf2x16(obbox.y);
        vec2 C = unpackHalf2x16(obbox.w);
        vec2 D = unpackHalf2x16(obbox.z);
        
        // do this properly, should be two triangle-box tests
        vec4 bbox = vec4(
            vec2(min(min(A, B), min(C, D))),
            vec2(max(max(A, B), max(C, D)))
        );
        if(((bbox.x > bounds.z) && (bbox.y > bounds.w))
            || ((bounds.x > bbox.z) && (bounds.y > bbox.w)))
        {
            mask |= (1u << index);
        }

#else // USE_OBBOX

        vec4 bbox = texelFetch(lightBBox, int(start), 0);
        if(((bbox.x > bounds.z) && (bbox.y > bounds.w))
            || ((bounds.x > bbox.z) && (bounds.y > bbox.w)))
        {
            mask |= (1u << index);
        }

#endif // USE_OBBOX

    }

    return mask;
}


void main()
{
    uvec2 outputPixel = uvec2(gl_FragCoord.xy);
    uvec2 tileId = outputPixel;
          tileId.x /= lightInfo.y;
    
    uint lightStart = 128u * (outputPixel.x % lightInfo.y);
    uint lightEnd = min(lightStart + 128u, lightInfo.x);

    vec2 tileStart = vec2(tileId) * tileInfo.xy + tileInfo.zw;
    vec2 tileEnd = tileStart + tileInfo.xy;
    vec4 tileBounds = vec4(min(tileStart, tileEnd), max(tileStart, tileEnd));

    outBitMask = uvec4(
        evaluateRange(lightStart, min(lightStart + 32u, lightInfo.x), tileBounds),          // [0, 32)
        evaluateRange(lightStart + 32u, min(lightStart + 64u, lightInfo.x), tileBounds),    // [32, 64)
        evaluateRange(lightStart + 64u, min(lightStart + 96u, lightInfo.x), tileBounds),    // [64, 96)
        evaluateRange(lightStart + 96u, min(lightStart + 128u, lightInfo.x), tileBounds)    // [96, 129)
    );
}
