#version 460 core

#include "common.glsl"
#include "intersection.glsl"


layout(binding=0) uniform sampler2D lightBboxs;
layout(binding=1) uniform sampler2D lights;
layout(binding=2) uniform sampler2D lightMap;

layout(location=0)  uniform float inverseTextureSize;

flat layout(location = 0) out vec3 radiusSqRadiusAndCompression;
flat layout(location = 1) out vec3 lightCol;
flat layout(location = 2) out float lightTextureV;
layout(location = 3) out vec2 localUv;


void main()
{
    int pointLightId = gl_VertexID / 6;

    vec4 bbox = texelFetch(lightBboxs, ivec2(0, pointLightId), 0);
    vec4 lightsDataA = texelFetch(lights, ivec2(0, pointLightId), 0);
    vec4 lightsDataB = texelFetch(lights, ivec2(1, pointLightId), 0);
    vec2 lightsP = lightsDataA.xy;

    int quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);
    vec2 P = vec2(
        ((quadId & 1) == 0) ? bbox.x : bbox.z,
        ((quadId & 2) == 0) ? bbox.y : bbox.w
    );

    gl_Position = vec4(P, 0., 1.);

    localUv = P - lightsP;
    radiusSqRadiusAndCompression = vec3(lightsDataA.z * lightsDataA.z,
                                        lightsDataA.z,
                                        lightsDataA.w);
    lightTextureV = (float(pointLightId) + 0.5) * inverseTextureSize;
    lightCol = lightsDataB.xyz;
}
