#version 460 core

#include "intersection.glsl"

layout(binding=0)   uniform sampler1D lines;
layout(binding=1)   uniform sampler2D lights;
layout(location=0)  uniform ivec2 numLightsAndLines;

layout(location=0) in vec2 angleAndLightId;
layout(location=0) out vec4 outPlane;


void main()
{
    vec2 direction = vec2(cos(angleAndLightId.x), sin(angleAndLightId.x));
    vec3 lightPosAndRadius = texelFetch(lights, ivec2(0, int(angleAndLightId.y)), 0).xyz;
    vec2 lightPos = lightPosAndRadius.xy;
    float lightRadius = lightPosAndRadius.z;

    vec4 plane = vec4(
        vec2(direction.x, direction.y),     // Orientation perpendicular to the direction
        65503.9f,                           // 65504.0 is the largest normal f16 number
        0.0                                 // mark as not used
    );

    float dist = 65503.9;
    vec2 lineSegmentEnd = direction * dist;
    int numLines = numLightsAndLines.y;

    for(int lineId=0; lineId<numLines; ++lineId)
    {
        vec4 line = texelFetch(lines, lineId, 0) - lightPos.xyxy;
        if(lineSegmentsIntersect(vec2(0.), lineSegmentEnd, line.xy, line.zw))
        {
            vec2 lineDirection = normalize(line.xy - line.zw);
            vec2 planeXY = vec2(-lineDirection.y, lineDirection.x);
            float planeW = dot(planeXY, line.xy);
        
            // Plane needs reorientating, as the origin is not on the signed side
            if(planeW > 0.)
            {
                planeXY = -planeXY;
                planeW = -planeW;
            }
            plane = vec4(planeXY, planeW, 1.0);
            dist = planeOriginIntersection2D(direction, plane.xyz);
            lineSegmentEnd = direction * dist;
        }
    }

    outPlane = plane;
}
