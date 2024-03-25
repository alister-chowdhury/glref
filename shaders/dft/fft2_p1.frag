#version 460 core

// First pass of generating a 2d DFT
// input and output are expected to be the same resolution.

#include "dft.glsli"

layout(binding = 0)  uniform sampler2D inTexture;
layout(location = 0) out vec2 outDFT;

void main()
{
    ivec2 textureSize = textureSize(inTexture, 0);
    int y = int(gl_FragCoord.y);
    DFTContext ctx = DFTContext_init(textureSize.x, floor(gl_FragCoord.x));
    for(int i=0; i < textureSize.x; ++i)
    {
        vec4 px = texelFetch(inTexture, ivec2(i, y), 0);

#if EXTRACT_RED
        px.xy = vec2(px.x, 0.0);
#elif EXTRACT_GREEN
        px.xy = vec2(px.y, 0.0);
#elif EXTRACT_BLUE
        px.xy = vec2(px.z, 0.0);
#elif EXTRACT_ALPHA
        px.xy = vec2(px.w, 0.0);
#elif USE_LUMA
        px.xy = vec2(dot(px.xyz, vec3(0.2125, 0.7154, 0.0721)), 0.0);
#endif

        DFTContext_add(ctx, i, px.xy);
    }
    outDFT = DFTContext_get(ctx);
}
