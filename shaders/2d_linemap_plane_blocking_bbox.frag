#version 460 core

#include "common.glsl"
#include "intersection.glsl"


layout(location=0) in float v;

layout(binding=0) uniform sampler2D linemap;
layout(binding=1) uniform sampler2D lights;
// .xy = lights, .zw = linemap
layout(location=0) uniform vec4 textureSizeAndInvSize;


layout(location=0) out vec4 bbox;


void main()
{
    int pointLightId = int(textureSizeAndInvSize.x * v);
    vec3 pointLightCenterAndRadius = texelFetch(lights, ivec2(0, pointLightId), 0).xyz;
    vec2 pointLightCenter = pointLightCenterAndRadius.xy;
    float radius = pointLightCenterAndRadius.z;
    
    vec4 bboxLocal = vec4(0.);

    int sampleCoord = 0;
    for(float x = textureSizeAndInvSize.w * 0.5;
            x < (1.0 + textureSizeAndInvSize.w * 0.5);
            x += textureSizeAndInvSize.w, ++sampleCoord)
    {
        float angle = (x - 0.5) * TWOPI;

        vec2 toPoint = vec2(cos(angle), sin(angle));
        toPoint *= planeOriginIntersection2D(toPoint,
                                                texelFetch(linemap, ivec2(sampleCoord, pointLightId), 0).xyz);


        bboxLocal.xy = min(bboxLocal.xy, toPoint);
        bboxLocal.zw = max(bboxLocal.zw, toPoint);
    }

    bboxLocal.xy = max(bboxLocal.xy, vec2(-radius, -radius));
    bboxLocal.zw = min(bboxLocal.zw, vec2(radius, radius));
    bbox = bboxLocal + pointLightCenter.xyxy;

}
