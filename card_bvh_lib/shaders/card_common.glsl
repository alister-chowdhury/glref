#ifndef CARD_COMMON_H
#define CARD_COMMON_H 1


#ifndef USING_LOAD_CARD_DATA
#define USING_LOAD_CARD_DATA 0
#endif


#if USING_LOAD_CARD_DATA

#ifndef CARD_DATA_BINDING
#error CARD_DATA_BINDING not set
#endif

layout(std430, binding = CARD_DATA_BINDING) buffer CardDataObjects_
{
    vec4 CardDataObjects[];
};


#endif


#define CARD_DATA_VEC4_STRIDE 4


struct CardData
{
    vec3 axisX;
    vec3 axisY;
    vec3 axisZ;
    vec3 origin;
    vec3 localExtent;
};



CardData unpackCardData(vec4 V0,
                        vec4 V1,
                        vec4 V2,
                        vec4 V3)
{
    CardData result;
    result.axisX = V0.xyz;
    result.axisY = V1.xyz;
    result.axisZ = V2.xyz;
    result.origin = vec3(V0.w, V1.w, V2.w);
    result.localExtent = V3.xyz;
    return result;
}



#if USING_LOAD_CARD_DATA

CardData loadCardData(uint index)
{
    return unpackCardData(
        CardDataObjects[index*CARD_DATA_VEC4_STRIDE + 0],
        CardDataObjects[index*CARD_DATA_VEC4_STRIDE + 1],
        CardDataObjects[index*CARD_DATA_VEC4_STRIDE + 2],
        CardDataObjects[index*CARD_DATA_VEC4_STRIDE + 3]
    );
}

#endif


// https://www.geogebra.org/m/nuqptz5p
bool cardIntersection(vec3 ro, vec3 rd, CardData card, inout float u, inout float v, inout float w)
{
    vec3 originOffset = ro - (card.origin + card.axisZ * card.localExtent);
    float t = -dot(card.axisZ, originOffset) / dot(card.axisZ, rd);
    if((t > 0) && (t < w))
    {
        vec3 projected = originOffset + t * rd;
        vec2 ndcUv = vec2(dot(card.axisX, projected), dot(card.axisY, projected));
        if(all(lessThan(abs(ndcUv), card.localExtent.xy)))
        {
            u = ndcUv.x / card.localExtent.x * 0.5 + 0.5;
            v = ndcUv.y / card.localExtent.y * 0.5 + 0.5;
            w = t;
            return true;
        }
    }
    return false;
}


vec3 getCardPoint(CardData card, uint index)
{

    if((index & 1) == 0)
    {
        card.localExtent.x = -card.localExtent.x;
    }
    if((index & 2) == 0)
    {
        card.localExtent.y = -card.localExtent.y;
    }

    return card.axisX * card.localExtent.x
            + card.axisY * card.localExtent.y
            + card.axisZ * card.localExtent.z
            + card.origin;
}


#if USING_LOAD_CARD_DATA

bool cardIntersection(vec3 ro, vec3 rd, uint objectIndex, inout float u, inout float v, inout float w)
{
    return cardIntersection(ro, rd, loadCardData(objectIndex), u, v, w);
}


vec3 getCardPoint(uint cardObject, uint index)
{
    return getCardPoint(loadCardData(cardObject), index);
}

#endif


#endif
