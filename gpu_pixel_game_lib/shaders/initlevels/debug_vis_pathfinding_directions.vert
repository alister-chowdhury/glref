#version 460 core

// dispatch LG_TRIANGLES, 128*128*6


#include "../common.glsli"
#include "../map_atlas_common.glsli"
#include "../pathfinding_common.glsli"


readonly layout(binding=1, r8ui)    uniform uimage2D mapAtlas;
readonly layout(binding=2, rg32ui)   uniform uimage2D roomDirections;

layout(location=0) uniform uvec2 targetLevelAndRoom;
layout(location=0) out vec2 outShapeNdc;

void main()
{
    int pixelId = gl_VertexID / 6;
    ivec2 levelCoord = ivec2(pixelId % 64, pixelId / 64);

    vec2 shapeNdc = vec2(0);
    vec4 ndc = vec4(0, 0, 0, 0);

    uint level = targetLevelAndRoom.x;
    uint targetRoomId = targetLevelAndRoom.y;

    MapAtlasLevelInfo atlasInfo = getLevelAtlasInfo(level);
    if(levelCoord.x < atlasInfo.size.x && levelCoord.y < atlasInfo.size.y)
    {

        float levelToScreenScale = 64.0 / float(max(atlasInfo.size.x, atlasInfo.size.y));
        ivec2 coord = levelCoord + ivec2(atlasInfo.offset);

        uint roomPixel = imageLoad(mapAtlas, coord).x;
        if(roomPixel != 0u)
        {
            uint direction = getDirectionToRoom(roomDirections, coord, targetRoomId);
            int vertexId = triangleToQuadVertexIdZ(gl_VertexID % 6);
            vec2 X = decodePathDirection(direction);
            vec2 uv = vec2((vertexId & 1), (vertexId >> 1));
            shapeNdc = uv * 2.0 - 1.0;

            shapeNdc = vec2(dot(X, shapeNdc),
                            dot(vec2(X.y, -X.x), shapeNdc));

            if((roomPixel - 1u) == targetRoomId)
            {
                shapeNdc = vec2(10.0);
            }

            ndc.xy = (vec2(levelCoord) + uv)
                   * levelToScreenScale
                   * (1.0/vec2(64))
                   * 2.0 - 1.0
                   ;
            ndc.zw = vec2(0.0, 1.0);

        }
    }

    outShapeNdc = shapeNdc;
    gl_Position = vec4(ndc);
}
