#version 460 core

#include "common.glsl"
#include "intersection.glsl"


layout(binding=0)   uniform sampler1D lines;
layout(binding=1)   uniform sampler2D lights;
layout(location=0)  uniform int startingPointLightID;
layout(location=1)  uniform vec2 inverseTextureSizeAndBias;


flat layout(location=0) out vec3 plane;
flat layout(location=1) out vec4 outLine;
layout(location=2) out float angle;


// Cull lines which are further than the radius
#define CULL_BY_RADIUS 1


void main()
{
    int pointLightId = startingPointLightID + gl_InstanceID;

    // polarOffset is used to account for lines that wrap around a circle
    // and create discontinuities, the easiest approach is to simply render them
    // twice.
    float polarOffset = ((gl_VertexID >> 1) & 1);
    int lineSide = (gl_VertexID & 1);
    int lineId = (gl_VertexID >> 2);

    vec3 lightPosAndRadius = texelFetch(lights, ivec2(0, pointLightId), 0).xyz;
    vec2 lightPos = lightPosAndRadius.xy;
    vec4 line = texelFetch(lines, lineId, 0) - lightPos.xyxy;

#if CULL_BY_RADIUS
    if(distanceToLineSq(vec2(0.), line.xy, line.zw) > (lightPosAndRadius.z * lightPosAndRadius.z))
    {
        plane = vec3(0);
        outLine = vec4(0);
        angle = 0;
        gl_Position = vec4(-1, -1, 2, 0);
        return;
    }
#endif

    // https://www.geogebra.org/calculator/qyfnsjdp
    float Ax = fastAtan2(line.y, line.x) * INVTWOPI + 0.5;
    float Bx = fastAtan2(line.w, line.z) * INVTWOPI + 0.5;

    vec2 sortedProjected = Ax < Bx ? vec2(Ax, Bx) : vec2(Bx, Ax);
    bool needsWrap = (sortedProjected.y - sortedProjected.x) > 0.5;
    vec2 wrapped = (needsWrap ? vec2(sortedProjected.y-1, sortedProjected.x) : sortedProjected);

    float bias = inverseTextureSizeAndBias.y;
    float currentX = lineSide == 0 ? wrapped.x - bias : wrapped.y + bias;
          currentX += polarOffset;

    float currentY = inverseTextureSizeAndBias.x * (float(pointLightId) + 0.5);
    gl_Position = vec4(vec2(currentX, currentY) * 2 - 1,
                        0.0, // Depth is calculated in the fragment shader
                        1.0);

    {        
        vec2 lineDirection = normalize(line.xy - line.zw);
        vec2 planeXY = vec2(-lineDirection.y, lineDirection.x);
        float planeW = dot(planeXY, line.xy);
    
        // Plane needs reorientating, as the origin is not on the signed side
        if(planeW < 0.)
        {
            planeXY = -planeXY;
            planeW = -planeW;
        }
        outLine = line;
        plane = vec3(planeXY, planeW);
        angle = (currentX - 0.5) * TWOPI;
    }

}
