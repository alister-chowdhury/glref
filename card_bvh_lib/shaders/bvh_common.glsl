#ifndef BVH_COMMON_H
#define BVH_COMMON_H 1


// Compute shader only
// Reduces vgpr_count by around 40 (depending on the max stack size)
#ifndef BVH_USE_SHARED_MEMORY
#define BVH_USE_SHARED_MEMORY 0
#endif

#define BVH_NODE_TYPE_NODE      0
#define BVH_NODE_TYPE_LEAF      1

#ifndef BVH_MAX_STACK_SIZE
#define BVH_MAX_STACK_SIZE 32
#endif

#ifndef USING_LOAD_BVH_DATA
#define USING_LOAD_BVH_DATA 0
#endif

#if USING_LOAD_BVH_DATA

#ifndef BVH_DATA_BINDING
#error BVH_DATA_BINDING not set
#endif

#include "card_common.glsl"

layout(rgba32f, binding=BVH_DATA_BINDING) uniform image1D BVHNodeHierarchy;

#endif // USING_LOAD_BVH_DATA


struct BVHNodeEntry
{
    vec4 V0;    // .xyz = bbox min, .w = type
    vec4 V1;    // .xyz = bbox max, .w = objectIndex
};


struct BVHNode
{
    BVHNodeEntry entries[2];
};


uint getType(BVHNodeEntry entry) { return floatBitsToUint(entry.V0.w); }
uint getObjectIndex(BVHNodeEntry entry) { return floatBitsToUint(entry.V1.w); }
vec3 getBBoxMin(BVHNodeEntry entry) { return entry.V0.xyz; }
vec3 getBBoxMax(BVHNodeEntry entry) { return entry.V1.xyz; }


#if USING_LOAD_BVH_DATA


BVHNodeEntry loadBvhEntry(uint offset)
{
    BVHNodeEntry entry;
    entry.V0 = imageLoad(BVHNodeHierarchy, int(offset));
    entry.V1 = imageLoad(BVHNodeHierarchy, int(offset+1));
    return entry;
}


uvec4 loadBvhLeafs(uint offset)
{
    return floatBitsToUint(imageLoad(BVHNodeHierarchy, int(offset)));
}



#if USING_LOAD_CARD_DATA



// https://www.geogebra.org/3d/rswecyg8
bool rayBoxIntersects(vec3 ro, vec3 invRd, vec3 boxMin, vec3 boxMax, inout float hitDist)
{
    vec3 plane0 = (boxMin - ro) * invRd;
    vec3 plane1 = (boxMax - ro) * invRd;
    vec3 near = min(plane0, plane1);
    vec3 far = max(plane0, plane1);
    float nearDist = max(near.x, max(near.y, near.z));
    float farDist = min(far.x, min(far.y, far.z));

    if(nearDist < farDist)
    {
        hitDist = max(0, nearDist);
        return true;
    }

    return false;
}


float safeInverse(float x)
{
    // can be bit-twiddled
    if(abs(x) < 8.27181e-25) { x = x < 0 ? -8.27181e-25 : 8.27181e-25; }
    return 1.0/x;
}


#if BVH_USE_SHARED_MEMORY

#ifndef BVH_GROUP_SIZE
#error BVH_GROUP_SIZE not set
#endif

uint traversalStackShared[BVH_MAX_STACK_SIZE * BVH_GROUP_SIZE];

#endif


void rayCastBvh(vec3 ro, vec3 rd, inout float hitT, inout uint hitObject, inout vec2 UV)
{

#if !BVH_USE_SHARED_MEMORY
    uint traversalStack[BVH_MAX_STACK_SIZE];
#endif

    vec3 invRd = vec3(safeInverse(rd.x), safeInverse(rd.y), safeInverse(rd.z));
    vec3 ood = invRd * ro;

    // Start from root node
    int traversalStackIndex = 0;

#if BVH_USE_SHARED_MEMORY
    traversalStackShared[BVH_MAX_STACK_SIZE * gl_LocalInvocationIndex] = 0;
#else
    traversalStack[0] = 0;
#endif

    while(traversalStackIndex >= 0)
    {

        uint foundLeafBin[2];
        foundLeafBin[0] = 0xffffffff;
        foundLeafBin[1] = 0xffffffff;

        // Recurse until we find atleast one bucket of triangles
        while((foundLeafBin[0] == 0xffffffff) && (foundLeafBin[1] == 0xffffffff) && (traversalStackIndex >= 0))
        {

#if BVH_USE_SHARED_MEMORY
            uint currentIndex = traversalStackShared[BVH_MAX_STACK_SIZE * gl_LocalInvocationIndex + traversalStackIndex--];
#else
            uint currentIndex = traversalStack[traversalStackIndex--];
#endif

            BVHNodeEntry entry0 = loadBvhEntry(currentIndex);
            BVHNodeEntry entry1 = loadBvhEntry(currentIndex + 1);

            float hitDist0;
            float hitDist1;
            bool hit0 = rayBoxIntersects(ro, invRd, getBBoxMin(entry0), getBBoxMax(entry0), hitDist0);
                 hit0 = hit0 && (hitDist0 < hitT);
            bool hit1 = rayBoxIntersects(ro, invRd, getBBoxMin(entry1), getBBoxMax(entry1), hitDist1);
                 hit1 = hit1 && (hitDist1 < hitT);

            // Move hit1 to hit0 if hit0 is not valid
            if(!hit0 && hit1)
            {
                hit0 = hit1;
                entry0 = entry1;
                hit1 = false;
            }

            if(hit0 || hit1)
            {
                // If both entries are valid candidates and of the same type
                // ensure hit0 is closer, so it can be evaluated first
                uint type0 = getType(entry0);
                uint type1 = getType(entry1);
                if(hit0 && hit1 && (type0 == type1))
                {
                    bool doSwap = (
                        ((type0 == BVH_NODE_TYPE_NODE) && (hitDist0 < hitDist1))
                        || ((type1 == BVH_NODE_TYPE_LEAF) && (hitDist1 < hitDist0))
                    );

                    if(doSwap)
                    {
                        BVHNodeEntry tmp = entry0;
                        entry0 = entry1;
                        entry1 = tmp;                        
                    }
                }

                if(hit0)
                {
                    uint objectIndex = getObjectIndex(entry0);

#if BVH_USE_SHARED_MEMORY
                    if(type0 == BVH_NODE_TYPE_NODE) { traversalStackShared[BVH_MAX_STACK_SIZE * gl_LocalInvocationIndex + traversalStackIndex++] = objectIndex; }
#else
                    if(type0 == BVH_NODE_TYPE_NODE) { traversalStack[traversalStackIndex++] = objectIndex; }
#endif
                    else { foundLeafBin[0] = objectIndex; }
                }

                if(hit1)
                {
                    uint objectIndex = getObjectIndex(entry1);
#if BVH_USE_SHARED_MEMORY
                    if(type1 == BVH_NODE_TYPE_NODE) { traversalStackShared[BVH_MAX_STACK_SIZE * gl_LocalInvocationIndex + traversalStackIndex++] = objectIndex; }
#else
                    if(type1 == BVH_NODE_TYPE_NODE) { traversalStack[traversalStackIndex++] = objectIndex; }
#endif
                    else { foundLeafBin[1] = objectIndex; }
                }
            }
        }


#if 0
        // Try to lock step the intersections
        if(foundLeafBin[0] == 0xffffffff)
        {
            foundLeafBin[0] = foundLeafBin[1];
            foundLeafBin[1] = 0xffffffff;
        }
#endif

        for(int i=0; i<2; ++i)
        {
            if(foundLeafBin[i] != 0xffffffff)
            {
                uvec4 cardObjects = loadBvhLeafs(foundLeafBin[i]);
                if(cardObjects.x != 0xffffffff)
                {
                    if(cardIntersection(ro, rd, cardObjects.x, UV.x, UV.y, hitT)) { hitObject = cardObjects.x; }
                    if(cardObjects.y != 0xffffffff)
                    {
                        if(cardIntersection(ro, rd, cardObjects.y, UV.x, UV.y, hitT)) { hitObject = cardObjects.y; }
                        if(cardObjects.z != 0xffffffff)
                        {
                            if(cardIntersection(ro, rd, cardObjects.z, UV.x, UV.y, hitT)) { hitObject = cardObjects.z; }
                            if(cardObjects.w != 0xffffffff)
                            {
                                if(cardIntersection(ro, rd, cardObjects.w, UV.x, UV.y, hitT)) { hitObject = cardObjects.w; }
                            }
                        }
                    }
                }
            }
        }
    }

}



#endif // USING_LOAD_CARD_DATA
#endif //USING_LOAD_BVH_DATA


#endif
