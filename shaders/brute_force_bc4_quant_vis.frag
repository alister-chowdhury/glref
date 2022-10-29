#version 460 core


layout(binding=0) uniform sampler2D alphaImage;
layout(binding=1)  uniform sampler2D iterationImage;

layout(location=0) uniform vec2 textureSize;


layout(location=0) in vec2 uv;
layout(location=0) out vec4 outCol;

#ifndef SHOW_BC_QUANTIZATION
#define SHOW_BC_QUANTIZATION 1
#endif


// Mode 0
// Basically a 3 bit linear interpolation (8 values)
float quantMode0(float value, float a, float b)
{
    float scale = 7.0f / (b - a);
    float proj = (value - a) * scale + 0.5f;
    int quantId = clamp(int(proj), 0, 7);
    float quantValue = float(quantId) / scale + a;
    return quantValue;
}

// Mode 1
// 6 values to interpolate between with 0 and 1 always
// being dedicated.
float quantMode1(float value, float a, float b)
{
    if(value == 0 || value == 1)
    {
        return value;
    }

    float scale = 5.0f / (b - a);
    float proj = (value - a) * scale + 0.5f;
    int quantId = clamp(int(proj), 0, 5);
    float quantValue = float(quantId) / scale + a;
    return quantValue;
}


float quant(float value, vec2 params)
{
    if(params.x < params.y)
    {
        return quantMode0(value, params.x, params.y);
    }
    return quantMode1(value, params.y, params.x);
}


void main()
{
    ivec2 coord = ivec2(uv * textureSize);
    float value = texelFetch(alphaImage, coord, 0).x;

#if SHOW_BC_QUANTIZATION    
    vec2 quantParams = texelFetch(iterationImage, coord >> 2, 0).xy;
    value = quant(value, quantParams.xy);
#endif // SHOW_BC_QUANTIZATION

    outCol = vec4(value, value, value, 1);
}