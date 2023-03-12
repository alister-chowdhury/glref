#version 460 core

layout(location=0) in vec2 UV;
layout(binding=0) uniform sampler1D lines;
layout(location=0) uniform int numLines;
layout(location=0) out float distanceField;


void main()
{
    float df = 1.0;
    vec2 P = UV;

    // Should really do a pass before hand to bucket these!
    for(int i=0; i<numLines; ++i)
    {
        // https://www.geogebra.org/calculator/xq2q58w4
        vec4 line = texelFetch(lines, i, 0);
        vec2 Ld = line.zw - line.xy;
        vec2 Ln = normalize(vec2(Ld.y, -Ld.x));
        
        vec2 L0 = line.xy - P;
        vec2 L1 = line.zw - P;
        float Lw = dot(Ln, L0);

        vec2 nearestPoint = Ln * Lw;

        // Clamp the point to the line ends
        if(dot(L0 - nearestPoint, -Ld) < 0)
        {
            nearestPoint = L0;
        }
        else if(dot(L1 - nearestPoint, Ld) < 0)
        {
            nearestPoint = L1;
        }

        float nearestDistSq = dot(nearestPoint, nearestPoint);
        df = min(df, nearestDistSq);
    }

    distanceField = sqrt(df);
}