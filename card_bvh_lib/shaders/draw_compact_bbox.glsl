
#ifndef Z_TO_Y_CONVERSION
#define Z_TO_Y_CONVERSION 1
#endif

#include "common.glsl"


layout(location = 0) uniform mat4 viewProjection;

layout(rgba32f, binding=0) uniform image1D cardBBoxs;



#ifdef DRAW_COMPACT_BBOX_VS


flat layout(location = 0) out vec3 outCol;

void main()
{

    uint cardId = gl_VertexID / 24;
    uint vertexId = gl_VertexID % 24;

#if Z_TO_Y_CONVERSION
    vec3 bboxMin = imageLoad(cardBBoxs, int(cardId * 2 + 0)).xzy;
    vec3 bboxMax = imageLoad(cardBBoxs, int(cardId * 2 + 1)).xzy;
#else
    vec3 bboxMin = imageLoad(cardBBoxs, int(cardId * 2 + 0)).xyz;
    vec3 bboxMax = imageLoad(cardBBoxs, int(cardId * 2 + 1)).xyz;
#endif

    vec3 P = getLineBBoxVertex(bboxMin, bboxMax, vertexId);

    gl_Position = viewProjection * vec4(P, 1.0);
    outCol = randomHs1Col(cardId);
}

#endif


#ifdef DRAW_COMPACT_BBOX_FS

flat layout(location = 0) in vec3 inCol;
layout(location = 0) out vec4 outCol;


void main()
{
    outCol = vec4(inCol, 0);
}

#endif
