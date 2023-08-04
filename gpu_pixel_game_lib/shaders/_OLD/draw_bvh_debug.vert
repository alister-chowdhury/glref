#version 460 core


// dispatch GL_LINES, 2 * 4 * 2 * 63)

#include "common.glsli"


readonly layout(std430, binding = 0) buffer bvh_ { vec4 bvh[]; };
layout(location=0) out vec3 col;

void main()
{
    uint idx = uint(gl_VertexID);
    uint pointId = idx & 1u; idx >>= 1;
    uint lineId = idx & 3u; idx >>= 2;
    uint bvhSide = idx & 1u; idx >>= 1;
    uint bvhId = idx;

    vec4 bbox = bvh[bvhId * 3 + 1 + bvhSide];
    vec2 uv = vec2(0);
    switch(lineId)
    {
        case 0: uv = (pointId == 0) ? bbox.xy : bbox.zy; break;
        case 1: uv = (pointId == 0) ? bbox.zy : bbox.zw; break;
        case 2: uv = (pointId == 0) ? bbox.zw : bbox.xw; break;
        case 3: uv = (pointId == 0) ? bbox.xw : bbox.xy; break;
        default: break;
    }

    col = vec3(1.0);//randomHs1Col(bvhId * 2u + bvhId);
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}

