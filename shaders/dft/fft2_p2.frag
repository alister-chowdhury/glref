#version 460 core

// Second pass of generating a 2d DFT
// input and output are expected to be the same resolution.

#include "dft.glsli"

layout(binding = 0)  uniform sampler2D inTexture;

#if OUTPUT_LENGTH
layout(location = 0) out float outDFT;
#else // OUTPUT_LENGTH
layout(location = 0) out vec2  outDFT;
#endif // OUTPUT_LENGTH

void main()
{
    ivec2 textureSize = textureSize(inTexture, 0);
    int x = int(gl_FragCoord.x);
    DFTContext ctx = DFTContext_init(textureSize.y, floor(gl_FragCoord.y));
    for(int i=0; i < textureSize.y; ++i)
    {
        vec4 px = texelFetch(inTexture, ivec2(x, i), 0);
        DFTContext_add(ctx, i, px.xy);
    }

#if OUTPUT_LENGTH
    outDFT = length(DFTContext_get(ctx));
#else // OUTPUT_LENGTH
    outDFT = DFTContext_get(ctx);
#endif // OUTPUT_LENGTH
}
