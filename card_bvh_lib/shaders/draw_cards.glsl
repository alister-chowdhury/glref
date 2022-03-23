
#ifndef NO_FACE_CULLING
#define NO_FACE_CULLING 1
#endif

#ifndef Z_TO_Y_CONVERSION
#define Z_TO_Y_CONVERSION 1
#endif


#define USING_LOAD_CARD_DATA    1
#define CARD_DATA_BINDING       0


#include "common.glsl"
#include "card_common.glsl"


layout(location = 0) uniform mat4 viewProjection;



#ifdef DRAW_CARDS_VS

flat layout(location = 0) out vec3 outCol;


void main()
{

    uint cardId = gl_VertexID / 6;
    uint vertexId = triangleToQuadId(gl_VertexID % 6, bool(NO_FACE_CULLING));

    vec3 P = getCardPoint(cardId, vertexId);

#if Z_TO_Y_CONVERSION
    P = P.xzy;
#endif

    gl_Position = viewProjection * vec4(P, 1.0);
    outCol = randomHs1Col(cardId);
}


#endif



#ifdef DRAW_CARDS_FS

flat layout(location = 0) in vec3 inCol;
layout(location = 0) out vec4 outCol;


void main()
{
    outCol = vec4(inCol, 0);
}

#endif
