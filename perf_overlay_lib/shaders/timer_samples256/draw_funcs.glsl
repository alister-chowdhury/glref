
#ifndef Y_STARTS_AT_BOTTOM
#define Y_STARTS_AT_BOTTOM 1
#endif

#include "timer_samples256.glslh"
#include "../number_encoding.glslh"


readonly layout(std430, binding = 0) buffer sampleData_
{
    TimerSamples256 sampleData;
};


layout(binding =1) uniform inputData_
{
    DrawTimerSamples256Input inputData;
};


const uint triangleVertexToQuad[6] = uint[6](
    0, 1, 2,
    2, 1, 3
);


///////////////////////////////////////////////////////////////
////////// Draw graph vertex shader
///////////////////////////////////////////////////////////////

#ifdef DRAW_GRAPH_VS

// u = [0, 1]
// v = [min value / max value]
noperspective layout(location = 0) out vec2 outUv;


void main()
{
    // Swap to triangle strips later
    const uint quadId = triangleVertexToQuad[gl_VertexID % 6];
    vec2 uv = vec2(float(quadId & 1), float(quadId >> 1));

    outUv = uv;
    outUv.y *= inputData.valueRanges.y - inputData.valueRanges.x;
    outUv.y += inputData.valueRanges.x;

    vec2 screenPos = mix(
#if !Y_STARTS_AT_BOTTOM
        inputData.graphScreenBounds.xw,
        inputData.graphScreenBounds.zy,
#else
        inputData.graphScreenBounds.xy,
        inputData.graphScreenBounds.zw,
#endif
        uv
    );

    gl_Position = vec4(screenPos * 2.0 - 1.0, 0.0, 1.0);

}

#endif


///////////////////////////////////////////////////////////////
////////// Draw graph fragment shader
///////////////////////////////////////////////////////////////

#ifdef DRAW_GRAPH_FS

// u = [0, 1]
// v = [min value / max value]
noperspective layout(location = 0) in vec2 uv;


layout(location = 0) out vec4 outCol;

void main()
{
    float value = timerSample(sampleData, uv.x);

    vec4 col;

    if(value < uv.y)
    {
        col = vec4(0.2, 0.2, 0.2, 0.5);
    }
    else
    {
        col = getSteppedValueColour(value, inputData);
        col.w = 0.9;
    }

    outCol = col;
}

#endif


///////////////////////////////////////////////////////////////
////////// Draw info numbers vertex shader
///////////////////////////////////////////////////////////////

#ifdef DRAW_GRAPH_INFO_VS


noperspective layout(location = 0) out vec2 uv;
flat layout(location = 1) out uint encodedNumber;
flat layout(location = 2) out vec4 fgCol;

void main()
{

    fgCol = getSteppedValueColour(
        getDisplayHistory(sampleData),
        inputData
    );
    encodedNumber = getHistoryText(sampleData);


    const uint quadId = triangleVertexToQuad[gl_VertexID % 6];
    uv = vec2(float(quadId & 1), float(quadId >> 1));

    vec2 screenPos = mix(

#if !Y_STARTS_AT_BOTTOM
        inputData.historyBounds.xw,
        inputData.historyBounds.zy,
#else
        inputData.historyBounds.xy,
        inputData.historyBounds.zw,
#endif
        uv
    );

    gl_Position = vec4(screenPos * 2.0 - 1.0, 0.0, 1.0);
}


#endif


///////////////////////////////////////////////////////////////
////////// Draw info numbers fragment shader
///////////////////////////////////////////////////////////////

#ifdef DRAW_GRAPH_INFO_FS


noperspective layout(location = 0) in vec2 uv;
flat layout(location = 1) in uint encodedNumber;
flat layout(location = 2) in vec4 fgCol;

layout(location = 0)        out vec4 outCol;

void main()
{
    uint signedValue = sampleEncodedNumber(encodedNumber, uv);
    outCol = (signedValue == 0) ? vec4(0.2, 0.2, 0.2, 0.0) : fgCol;
}


#endif



///////////////////////////////////////////////////////////////
////////// Draw barrier lines vertex shader
///////////////////////////////////////////////////////////////

#ifdef DRAW_GRAPH_LINES_VS

flat layout(location = 0) out vec4 fgCol;

void main()
{

    const uint lineId = gl_VertexID / 2;
    const uint lineSide = gl_VertexID % 2;

    fgCol = lineId == 0 ? vec4(1.0, 1.0, 0.0, 0.5) : vec4(1.0, 0.0, 0.0, 0.5);
    
    float v = lineId == 0 ? inputData.valueRanges.z : inputData.valueRanges.w;
    v -= inputData.valueRanges.x;
    v /= (inputData.valueRanges.y - inputData.valueRanges.x);

#if !Y_STARTS_AT_BOTTOM
    v = mix(inputData.graphScreenBounds.w, inputData.graphScreenBounds.y, v);
#else
    v = mix(inputData.graphScreenBounds.y, inputData.graphScreenBounds.w, v);
#endif
    float u = lineSide == 0 ? inputData.graphScreenBounds.x : inputData.graphScreenBounds.z;

    vec2 uv = vec2(u, v);
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}


#endif


///////////////////////////////////////////////////////////////
////////// Draw barrier lines fragment shader
///////////////////////////////////////////////////////////////

#ifdef DRAW_GRAPH_LINES_FS

flat layout(location = 0) in vec4 fgCol;

layout(location = 0) out vec4 col;


void main()
{
    col = fgCol;
}

#endif
