#version 460 core

layout(binding=0) uniform sampler2D prevAnisoDistanceField;
layout(location=0) out vec4 anisoDistanceField;

void main()
{
    ivec2 base = ivec2(gl_FragCoord.xy) * 2;
    anisoDistanceField = min(
        min(
            texelFetch(prevAnisoDistanceField, base, 0),
            texelFetch(prevAnisoDistanceField, base + ivec2(1, 0), 0)
        ),
        min(
            texelFetch(prevAnisoDistanceField, base + ivec2(0, 1), 0),
            texelFetch(prevAnisoDistanceField, base + ivec2(1, 1), 0)
        )
    );
}