#ifndef INTERSECTION_GLSL_H
#define INTERSECTION_GLSL_H


// https://www.geogebra.org/calculator/jenewbrk
float planeOriginIntersection2D(vec2 direction, vec3 plane)
{
    return 1.0 / (plane.z * dot(direction, plane.xy));
}


// https://www.geogebra.org/calculator/ytnhzgzb
bool lineSegmentsIntersectFromDeltas(vec2 AB, vec2 CD, vec2 AC)
{
    float d = AB.x * CD.y - AB.y * CD.x;
    float u = AC.x * AB.y - AC.y * AB.x;
    float v = AC.x * CD.y - AC.y * CD.x;

    // u *= sign(d);
    // v *= sign(d);
    uint signMask = floatBitsToUint(d) & 0x80000000u;
    u = uintBitsToFloat(floatBitsToUint(u) ^ signMask);
    v = uintBitsToFloat(floatBitsToUint(v) ^ signMask);

    return (min(u, v) > 0.) && (max(u, v) < abs(d));
}


bool lineSegmentsIntersect(vec2 A, vec2 B, vec2 C, vec2 D)
{
    vec2 AB = A - B;
    vec2 CD = C - D;
    vec2 AC = A - C;
    return lineSegmentsIntersectFromDeltas(AB, CD, AC);
}


// https://www.geogebra.org/calculator/dug27m5r
vec2 rayLineIntersectionPoint(vec2 ro, vec2 rd, vec2 lineA, vec2 lineB)
{
    vec2 BA = lineB - lineA;
    float denom = BA.x * rd.y - rd.x * BA.y;

    // Interval from lineA => lineB
    vec2 lineAOffset = lineA - ro;
    float u = (rd.x * lineAOffset.y - rd.y * lineAOffset.x) / denom;

    return lineA + BA * u;
}


bool rayIntersectsLine(vec2 ro, vec2 rd, vec2 lineA, vec2 lineB)
{
    vec2 BA = lineB - lineA;
    float denom = BA.x * rd.y - rd.x * BA.y;
    
    lineA -= ro;
    float u = (rd.x * lineA.y - rd.y * lineA.x);

    // u *= sign(denom);
    uint signMask = floatBitsToUint(denom) & 0x80000000u;
    u = uintBitsToFloat(floatBitsToUint(u) ^ signMask);

    return (0.0 < u) && (u < abs(denom));
}


// Takes a bias to mimic penumbra (only affects the edges of C and D)
// e.g:
//      float baseBias = 0.4;
//      vec2 A = uv;
//      vec2 B = lightPos;
//      vec2 C = line.xy;
//      vec2 D = line.xy;
//      float mdist = sqrt(sqrt(min(dot(C-A, C-A), dot(D-A, D-A))));
//      float visibility = 1.0 - lineSegmentsIntersectBiasedCD(A, B, C, D, baseBias * min(0.1, mdist));
//
float lineSegmentsIntersectBiasedCD(vec2 A, vec2 B, vec2 C, vec2 D, float bias)
{
    vec2 AB = A - B;
    vec2 CD = C - D;
    vec2 AC = A - C;

    float d = AB.x * CD.y - AB.y * CD.x;
    float u = AC.x * AB.y - AC.y * AB.x;
    float v = AC.x * CD.y - AC.y * CD.x;

    // v *= sign(d);
    uint signMask = floatBitsToUint(d) & 0x80000000u;
    v = uintBitsToFloat(floatBitsToUint(v) ^ signMask);

    if((v <= 0.) || (v >= abs(d)))
    {
        return 0.;
    }

    u /= d;
    u = abs(u * 2. - 1.);
    return 1.0-smoothstep(1.-bias, 1.+bias, u);
}


#endif
