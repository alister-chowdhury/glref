#version 460 core

#include "../common.glsl"

readonly layout(std430, binding = 0) buffer bvh_ { vec4 bvh[]; };
layout(location=0) out vec3 col;



uint wang_hash(uint seed)
{
    seed = (seed ^ 61) ^ (seed >> 16);
    seed *= 9;
    seed = seed ^ (seed >> 4);
    seed *= 0x27d4eb2d;
    seed = seed ^ (seed >> 15);
    return seed;
}


vec3 hs1(float H)
{
    float R = abs(H * 6 - 3) - 1;
    float G = 2 - abs(H * 6 - 2);
    float B = 2 - abs(H * 6 - 4);
    return clamp(vec3(R,G,B), vec3(0), vec3(1));
}


vec3 randomHs1Col(uint idx)
{
    return hs1((wang_hash(idx) & 0xffff) / 65535.0);
}

void main()
{

#define MODE 0

    // Fill
#if DEBUG_LEVEL_BBOXES
    int quadId = triangleToQuadVertexIdZ(gl_VertexID % 6);
    int bboxId = gl_VertexID / 6;
    vec4 bbox = bvh[bboxId];
#else // DEBUG_LEVEL_BBOXES
    int idx = gl_VertexID;
    int quadId = triangleToQuadVertexIdZ(idx % 6);
    idx /= 6;
    int bboxId = idx % 2; idx /= 2;
    int bvhId = idx;
    vec4 bbox = bvh[3 * bvhId + 1 + bboxId];

    bboxId = bboxId * 2 + bvhId;
#endif // DEBUG_LEVEL_BBOXES

    vec2 uv = vec2(
        ((quadId & 1) == 0) ? bbox.x : bbox.z,
        ((quadId & 2) == 0) ? bbox.y : bbox.w
    );

    float bboxArea = ((bbox.z - bbox.x) * (bbox.w - bbox.y));
    if((bboxArea <= 0) || (bbox.z < bbox.x) || (bbox.w < bbox.y))
    {
        uv = vec2(0);
        bboxArea = 0;
    }

    float depth = 1.0 - 1.0 / (1.0 + bboxArea);
    col = randomHs1Col(bboxId) / (1.0 + bboxArea);

    gl_Position = vec4(uv * 2.0 - 1.0, depth, 1.0);
}

