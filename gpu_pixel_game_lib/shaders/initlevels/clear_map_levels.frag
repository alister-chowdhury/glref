#version 460 core


#include "../map_atlas_common.glsli"


layout(location=0) out uint tileId;

void main()
{
    tileId = MAP_ATLAS_WALL_ID_NONE;
}
