#version 460 core


#include "common.glsli"


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 


readonly layout(std430, binding = 1) buffer drawCmds_ { vec4 drawCmds[]; };


void main()
{
    uint drawId = gl_VertexID / 6;
    uint quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);
    vec4 drawCmd = drawCmds[drawId];

    gl_Position = vec4(
        vec2(
            ((quadId & 1) == 0) ? drawCmd.x : drawCmd.z,
            ((quadId & 2) == 0) ? drawCmd.y : drawCmd.w
        ) * 2.0 - 1.0,
        0.0,
        1.0
    );

}
