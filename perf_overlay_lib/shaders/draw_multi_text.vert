#version 460


#ifndef Y_STARTS_AT_BOTTOM
#define Y_STARTS_AT_BOTTOM 1
#endif


struct PackedTextDataEntry
{
    vec4 bounds;

    // .x = offset to characters
    // .y = numCharacters
    // .z = packedBgCol (8bit RGBA)
    // .w = packedFgCol (8bit RGBA)
    uvec4   data;
};


readonly layout(std430, binding = 1) buffer textData_
{
    uint           textData[];
};


noperspective layout(location = 0) out vec2 uv;
flat layout(location = 1) out uint chractersOffset;
flat layout(location = 2) out float numCharacters;
flat layout(location = 3) out vec4 fgCol;
flat layout(location = 4) out vec4 bgCol;


const uint triangleVertexToQuad[6] = uint[6](
    0, 1, 2,
    2, 1, 3
);


PackedTextDataEntry loadPackedTextDataEntry(uint idx)
{
    PackedTextDataEntry result;
    result.bounds = vec4(
        uintBitsToFloat(textData[idx * 8 + 0]),
        uintBitsToFloat(textData[idx * 8 + 1]),
        uintBitsToFloat(textData[idx * 8 + 2]),
        uintBitsToFloat(textData[idx * 8 + 3])
    );
    result.data = uvec4(
        textData[idx * 8 + 4],
        textData[idx * 8 + 5],
        textData[idx * 8 + 6],
        textData[idx * 8 + 7]
    );
    return result;
}


void main()
{
    PackedTextDataEntry packedTextDataEntry = loadPackedTextDataEntry(gl_VertexID / 6);

    chractersOffset = packedTextDataEntry.data.x;
    numCharacters = float(packedTextDataEntry.data.y);
    bgCol = unpackUnorm4x8(packedTextDataEntry.data.z);
    fgCol = unpackUnorm4x8(packedTextDataEntry.data.w);

    const uint quadId = triangleVertexToQuad[gl_VertexID % 6];

    uv = vec2(float(quadId & 1), float(quadId >> 1));

    vec2 screenPos = mix(
#if Y_STARTS_AT_BOTTOM
        packedTextDataEntry.bounds.xw,
        packedTextDataEntry.bounds.zy,
#else
        packedTextDataEntry.bounds.xy,
        packedTextDataEntry.bounds.zw,
#endif
        uv
    );
    
    gl_Position = vec4(screenPos * 2.0 - 1.0, 0.0, 1.0);
}
