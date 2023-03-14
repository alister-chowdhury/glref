#version 460 core


layout(binding=0) uniform sampler2D noiseEnergy;
layout(location=0) uniform vec2 srcTextureSize;

layout(location=0) in vec2 uv;
layout(location=0) out vec4 outCol;

void main()
{

#if TILE_SAMPLE
    ivec2 coord = ivec2(fract(gl_FragCoord.xy / srcTextureSize) * srcTextureSize);
#else // TILE_SAMPLE
    ivec2 coord = ivec2(uv * srcTextureSize);
#endif // TILE_SAMPLE

    float value = texelFetch(noiseEnergy, coord, 0).x;
    outCol = vec4(value, value, value, 1);
}
