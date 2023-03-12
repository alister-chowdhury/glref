#version 460 core

layout(binding=0) uniform sampler2D prevDistanceField;
layout(location=0) out float distanceField;

void main()
{
    ivec2 base = ivec2(gl_FragCoord.xy) * 2;
    distanceField = min(
        min(
            texelFetch(prevDistanceField, base, 0).x,
            texelFetch(prevDistanceField, base + ivec2(1, 0), 0).x
        ),
        min(
            texelFetch(prevDistanceField, base + ivec2(0, 1), 0).x,
            texelFetch(prevDistanceField, base + ivec2(1, 1), 0).x
        )
    );
}