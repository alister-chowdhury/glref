#version 460 core

#include "common.glsl"
#include "intersection.glsl"


layout(binding=0)   uniform sampler2D linemap;
layout(binding=1)   uniform sampler2D lights;
layout(location=0)  uniform int lightId;
layout(location=1)  uniform float inverseTextureSize;


void main()
{
    vec2 lightPos = texelFetch(lights, ivec2(0, lightId), 0).xy;
    vec2 P = lightPos;

    if((gl_VertexID & 1) == 1)
    {
        vec4 planeAndVisible = texelFetch(linemap, ivec2(gl_VertexID >> 1, lightId), 0).xyzw;
        if(planeAndVisible.w > 0.)
        {
            vec3 plane = planeAndVisible.xyz;
            float u = inverseTextureSize * (float(gl_VertexID >> 1) + 0.5);
            float angle = (u - 0.5) * TWOPI;
            vec2 direction = vec2(cos(angle), sin(angle));
            P += direction * planeOriginIntersection2D(direction, plane);            
        }
    }

    gl_Position = vec4(P, 0., 1.);
}
