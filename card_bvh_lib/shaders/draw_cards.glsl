
#ifndef NO_FACE_CULLING
#define NO_FACE_CULLING 1
#endif

#ifndef Z_TO_Y_CONVERSION
#define Z_TO_Y_CONVERSION 1
#endif


#define USING_LOAD_CARD_DATA    1
#define CARD_DATA_BINDING       0


#include "card_common.glsl"


layout(location = 0) uniform mat4 viewProjection;



#ifdef DRAW_CARDS_VS

flat layout(location = 0) out vec3 outCol;


vec3 hs1(float H)
{
    float R = abs(H * 6 - 3) - 1;
    float G = 2 - abs(H * 6 - 2);
    float B = 2 - abs(H * 6 - 4);
    return clamp(vec3(R,G,B), vec3(0), vec3(1));
}


// https://www.reedbeta.com/blog/quick-and-easy-gpu-random-numbers-in-d3d11/
uint wang_hash(uint seed)
{
    seed = (seed ^ 61) ^ (seed >> 16);
    seed *= 9;
    seed = seed ^ (seed >> 4);
    seed *= 0x27d4eb2d;
    seed = seed ^ (seed >> 15);
    return seed;
}



void main()
{

    uint cardId = gl_VertexID / 6;
    uint vertexId = gl_VertexID % 6;

    // 0, 1, 2
    // 1, 2, 3
    if(vertexId >= 3)
    {
        vertexId -= 2;
#if !NO_FACE_CULLING
        // 2, 1, 3
        vertexId = 4 - ((vertexId - 1) % 3 + 1);
#endif
    }

    vec3 P = getCardPoint(cardId, vertexId);

#if Z_TO_Y_CONVERSION
    P = P.xzy;
#endif

    gl_Position = viewProjection * vec4(P, 1.0);
    outCol = hs1((wang_hash(cardId) & 0xffff) / 65535.0);
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
