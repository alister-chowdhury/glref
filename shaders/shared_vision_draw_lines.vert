#version 460 core

layout(binding=0) uniform sampler1D lines;


#if NO_WORLD_TO_CLIP
#else
layout(location=0) uniform mat3 worldToClip;
#endif

void main()
{
    vec4 line = texelFetch(lines, int(gl_VertexID >> 1), 0).xyzw;
    vec2 P = ((gl_VertexID & 1) == 0) ? line.xy : line.zw;

#if !NO_WORLD_TO_CLIP
    P = (worldToClip * vec3(P, 1.)).xy;
#endif

    gl_Position = vec4(P, 0., 1.);
}
