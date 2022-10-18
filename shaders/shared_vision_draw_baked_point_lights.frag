#version 460 core


layout(binding=0) uniform sampler2D bakedLighting;
layout(location = 0) in vec2 uv;
layout(location = 0) out vec3 col;


void main()
{
    col = texture(bakedLighting, uv).xyz;
}

