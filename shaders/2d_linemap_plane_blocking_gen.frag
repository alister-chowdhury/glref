#version 460 core

#include "intersection.glsl"


flat layout(location=0) in vec3 plane;
layout(location=1) in float angle;
layout(location=0) out vec4 outPlane;


void main()
{
    outPlane = vec4(plane, 1.0);
    vec2 direction = vec2(cos(angle), sin(angle));
    float dist = planeOriginIntersection2D(direction, plane);
    gl_FragDepth = 1.0 - 1.0 / (1.0 + dist);
}
