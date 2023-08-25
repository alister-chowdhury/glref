#version 460 core


#include "../map_atlas_common.glsli"


void main()
{
    vec2 ndc = vec2(
        gl_VertexID == 0 ? -4.0 : 1.0,
        gl_VertexID == 2 ? 4.0 : -1.0
    );
    const float depth = float(MAP_ATLAS_WALL_DEPTH_NONE) / float(0xffff);
    gl_Position = vec4(ndc, depth / float, 1.);
}
