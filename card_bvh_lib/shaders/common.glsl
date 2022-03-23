#ifndef COMMON_H
#define COMMON_H


vec3 UNIT_BOX_LINE_VERTEX[24] = vec3[24](
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


vec3 getUnitBoxLineVertex(uint lineVertexId)
{
    return UNIT_BOX_LINE_VERTEX[lineVertexId];
}


vec3 getLineBBoxVertex(vec3 bboxMin, vec3 bboxMax, uint lineVertexId)
{
    return mix(bboxMin, bboxMax, getUnitBoxLineVertex(lineVertexId));
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


uint triangleToQuadId(uint vertexId, bool noFaceCulling)
{
    // 0, 1, 2
    // 1, 2, 3
    if(vertexId >= 3)
    {
        vertexId -= 2;
        if(!noFaceCulling)
        {
            // 2, 1, 3
            vertexId = 4 - ((vertexId - 1) % 3 + 1);            
        }
    }
    return vertexId;
}


#endif
