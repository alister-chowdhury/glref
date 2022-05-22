#version 460 core


layout(location=0) in float angle;
layout(location=0) out vec4 outPlane;


void main()
{
    vec2 plane = vec2(sin(-angle), cos(angle));
    outPlane = vec4(
        vec2(-sin(angle), cos(angle)),  // Orientation perpendicular to the direction
        65503.9f,                       // 65504.0 is the largest normal f16 number
        0.0                             // mark as not used
    );
}
