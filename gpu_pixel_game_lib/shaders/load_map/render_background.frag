#version 460 core

readonly layout(binding=3, rgba8) uniform image2D assetBaseAtlas;
readonly layout(binding=4, rgba8) uniform image2D assetNormAtlas;

layout(location=0) in vec3 pixelCoordAndHeight;
layout(location=0) out vec4 outBase;
layout(location=1) out vec4 outNormals;

void main()
{
    ivec2 coord = ivec2(pixelCoordAndHeight.xy);
    outBase = imageLoad(assetBaseAtlas, coord);
    outNormals = vec4(imageLoad(assetNormAtlas, coord).xyz, pixelCoordAndHeight.z);
}
