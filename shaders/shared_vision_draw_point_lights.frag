#version 460 core

#include "common.glsl"
#include "intersection.glsl"


layout(binding=0) uniform sampler2D lightBboxs;
layout(binding=1) uniform sampler2D lights;
layout(binding=2) uniform sampler2D lightMap;

layout(location=0)  uniform float inverseTextureSize;


flat layout(location = 0) in vec3 radiusSqRadiusAndCompression;
flat layout(location = 1) in vec3 lightCol;
flat layout(location = 2) in float lightTextureV;
layout(location = 3) in vec2 localUv;

layout(location = 0) out vec3 col;

void main()
{

    float radiusSq = radiusSqRadiusAndCompression.x;
    float radius = radiusSqRadiusAndCompression.y;
    float compression = radiusSqRadiusAndCompression.z;

    vec3 C = vec3(0.);
    float lengthSq = dot(localUv, localUv);

    if(lengthSq < radiusSq)
    {
        float angle = fastAtan2(localUv.y, localUv.x);
        float u = angle * INVTWOPI + 0.5;
        vec4 plane = texture(lightMap, vec2(u, lightTextureV));

        // // looks weird at corners
        // plane.xy = normalize(plane.xy);

        float occlusion = smoothstep(-0.005, 0.005, dot(localUv, plane.xy) - plane.z)
                          * plane.w
                          ;

        if(occlusion < 1.)
        {
            // Based off:
            // https://stackoverflow.com/a/37755258
            float attenuation = pow(smoothstep(0, radius, sqrt(lengthSq)), compression);
            C = lightCol * (1.0 - attenuation) * (1.0 - occlusion);
        }
    }

    col = C;
}
