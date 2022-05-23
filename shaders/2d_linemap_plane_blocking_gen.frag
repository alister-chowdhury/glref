#version 460 core

#include "intersection.glsl"


flat layout(location=0) in vec3 plane;
flat layout(location=1) in vec4 line;
layout(location=2) in float angle;

layout(location=0) out vec4 outPlane;


void main()
{
    vec2 direction = vec2(cos(angle), sin(angle));

    if(!rayIntersectsLine(vec2(0.), direction, line.xy, line.zw))
    {
        discard;
    }

    outPlane = vec4(plane, 1.0);
    float dist = planeOriginIntersection2D(direction, plane);
    // gl_FragDepth = 1.0 - 1.0 / (1.0 + dist);
    gl_FragDepth = dist * 0.125;
}
