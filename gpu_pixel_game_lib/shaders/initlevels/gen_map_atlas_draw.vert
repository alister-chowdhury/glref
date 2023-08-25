#version 460 core

#include "../common.glsli"
#include "mapgen_common.glsli" 


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 


readonly layout(std430, binding = 1) buffer drawCmds_ { uvec2 drawCmds[]; };


layout(location=0) out uint type;


void main()
{
    unpackDrawCommandCoord(drawCmds[gl_VertexID / 6],
                           triangleToQuadVertexIdZ(gl_VertexID % 6),
                           gl_Position,
                           type);
}
