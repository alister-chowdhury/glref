
#ifndef Z_TO_Y_CONVERSION
#define Z_TO_Y_CONVERSION 1
#endif


layout(location = 0) uniform mat4 viewProjection;

layout(rgba32f, binding=0) uniform image1D cardBBoxs;



#ifdef DRAW_COMPACT_BBOX_VS


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


vec3 bboxEdgeLut[24] = vec3[24](
    vec3(0, 0, 0), vec3(1, 0, 0),
    vec3(0, 0, 0), vec3(0, 0, 1),
    vec3(1, 0, 0), vec3(1, 0, 1),
    vec3(1, 1, 0), vec3(1, 1, 1),
    vec3(0, 0, 1), vec3(0, 1, 1),
    vec3(1, 0, 1), vec3(1, 1, 1),
    vec3(0, 1, 0), vec3(1, 1, 0),
    vec3(0, 1, 1), vec3(1, 1, 1),
    vec3(0, 0, 0), vec3(0, 1, 0),
    vec3(0, 0, 1), vec3(1, 0, 1),
    vec3(0, 1, 0), vec3(0, 1, 1),
    vec3(1, 0, 0), vec3(1, 1, 0)
);



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

    vec3 L = bboxEdgeLut[vertexId];
    vec3 P = mix(bboxMin, bboxMax, L);

    gl_Position = viewProjection * vec4(P, 1.0);
    outCol = hs1((wang_hash(cardId) & 0xffff) / 65535.0);
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
