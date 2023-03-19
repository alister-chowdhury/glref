#version 460 core

#include "../../../shaders/common.glsl"


layout(location=0) out vec2 uv;
layout(location=1) out vec2 innerNDC;

layout(location=2) uniform vec3 spherePositionAndSize;


void main()
{
    int vertexId = int(gl_VertexID);
    int quadId = triangleToQuadVertexIdZ(vertexId % 6);
    float offsetX = ((quadId & 1) == 0) ? -1 : 1;
    float offsetY = ((quadId & 2) == 0) ? -1 : 1;

    innerNDC = vec2(offsetX, offsetY);
    uv = spherePositionAndSize.xy + innerNDC * spherePositionAndSize.z;
    gl_Position = vec4(uv * 2 - 1, 0.0, 1.0);
}
