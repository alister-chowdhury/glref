#version 460 core


#include "common.glsli"


layout(set=0, binding = 0) uniform GlobalParameters_
{
    GlobalParameters globals;
}; 


#if DEBUG_OUTPUT
layout(location = 0) out vec4 value;
#else
layout(location = 0) out uint value;
#endif

void main()
{
#if DEBUG_OUTPUT
    value = vec4(1.0, 1.0, 1.0, 1.0);
#else
    value = 0xffu;
#endif
}
