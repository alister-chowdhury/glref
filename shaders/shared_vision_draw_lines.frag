#version 460 core

layout(binding=0) uniform sampler1D lines;


#if NO_WORLD_TO_CLIP
layout(location=0) uniform vec3 col;
#else
layout(location=0) uniform mat3 worldToClip;
layout(location=1) uniform vec3 col;
#endif

layout(location = 0) out vec4 outRgba;

void main()
{
    outRgba = vec4(col, 1.);
}
