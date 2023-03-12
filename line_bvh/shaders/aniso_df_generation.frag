#version 460 core

layout(location=0) in vec2 UV;
layout(binding=0) uniform sampler1D lines;
layout(location=0) uniform int numLines;
layout(location=0) out vec4 anisoDistanceField;


float cross2d(vec2 a, vec2 b)
{
    return a.x * b.y - a.y * b.x;
}


void main()
{
    // .x = left
    // .y = up
    // .z = right
    // .w = down
    vec4 df = vec4(1.);
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

        bool nearestSideIsX = abs(nearestPoint.x) > abs(nearestPoint.y);
        float nearestDistSq = dot(nearestPoint, nearestPoint);

        if(nearestSideIsX)
        {
            // left
            if(nearestPoint.x < 0) { df.x = min(df.x, nearestDistSq); }
            // right
            else                   { df.z = min(df.z, nearestDistSq); }
        }
        else
        {
            // down
            if(nearestPoint.y < 0) { df.w = min(df.w, nearestDistSq); }
            // up
            else                   { df.y = min(df.y, nearestDistSq); }
        }


        // Intersect diagonally, so can figure out where a
        // line clips with segments adjacent to the segment
        // that contains the closest point
        //  e.g: If the nearest point is in the RIGHT sector
        //       it may also clip the UP and DOWN sector.
        float u0 = cross2d(vec2(-1, -1), L0) / cross2d(Ld, vec2(-1, -1));
        if(u0 > 0 && u0 < 1)
        {
            vec2 intersection = L0 + Ld * u0;
            float intersectionLenSq = dot(intersection, intersection);
            // left
            if(intersection.x < 0) { df.x = min(df.x, intersectionLenSq); }
            // right
            else                   { df.z = min(df.z, intersectionLenSq); }
            // down
            if(intersection.y < 0) { df.w = min(df.w, intersectionLenSq); }
            // up
            else                   { df.y = min(df.y, intersectionLenSq); }
        }
        
        float u1 = cross2d(vec2(1, -1), L0) / cross2d(Ld, vec2(1, -1));
        if(u1 > 0 && u1 < 1)
        {
            vec2 intersection = L0 + Ld * u1;
            float intersectionLenSq = dot(intersection, intersection);
            // left
            if(intersection.x < 0) { df.x = min(df.x, intersectionLenSq); }
            // right
            else                   { df.z = min(df.z, intersectionLenSq); }
            // down
            if(intersection.y < 0) { df.w = min(df.w, intersectionLenSq); }
            // up
            else                   { df.y = min(df.y, intersectionLenSq); }
        }
    }

    // Testing:
    // // outputting just a DF (much simpler and seems to mostly just "work" with bilinear interp)
    // df = vec4(min(min(df.x, df.y), min(df.z, df.w)));
    
    // // X/Y aniso
    // df.xz = vec2(min(df.x, df.z));
    // df.yw = vec2(min(df.y, df.w));
    anisoDistanceField = sqrt(df);
}