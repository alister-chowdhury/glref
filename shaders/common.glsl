#ifndef COMMON_GLSL_H
#define COMMON_GLSL_H

#define PI          3.141592653589793238462643383279502884197169399
#define HALFPI      1.5707963267948966192313216916397514420985847
#define TWOPI       6.283185307179586476925286766559005768394338799
#define INVPI       0.3183098861837906715377675267450287240689192915
#define INVTWOPI    0.1591549430918953357688837633725143620344596457
#define SQRT2       1.414213562373095048801688724209698078569671875
#define INVSQRT2    0.7071067811865475244008443621048490392848359377


float multiplySign(float x, float y)
{
    return uintBitsToFloat(floatBitsToUint(x) ^ (floatBitsToUint(y) & 0x80000000u));
}


// y = 1/x
// Only works if x is a power of 2
// if x = 0, result it 1.70141183E+38
float rcpForPowersOf2(float x)
{
    return uintBitsToFloat(0x7f000000u - floatBitsToUint(x));
}

// https://math.stackexchange.com/a/1105038
float fastAtan2(float y, float x)
{
    float a = min(abs(x), abs(y)) / max(abs(x), abs(y));
    float s = a * a;
    float r = ((-0.0464964749 * s + 0.15931422) * s - 0.327622764) * s * a + a;
    if(abs(y) > abs(x)) { r = HALFPI - r; }
    if(x < 0) { r = PI - r; }
    r = multiplySign(r, y); // if(y < 0) { r = -r; }
    return r;
}


// Similar to fastAtan2, except the result is pre divided by 2pi, for the
// purpose of sampling 1d circular maps (circular shadows etc).
// https://www.geogebra.org/calculator/dms6kp8w
//
// max error ~ 0.00024531353567275316
float fastAtan2_div2pi(float y, float x)
{
    float a = min(abs(x), abs(y)) / max(abs(x), abs(y));
    float s = a * a;
    float r = ((0.013506162438972577 * s + -0.04684240210645093) * s + -0.8414151531876038) * a + a;
    if(abs(y) > abs(x)) { r = 0.25 - r; }
    if(x < 0.0) { r = 0.5 - r; }
    r = multiplySign(r, y); // if(y < 0) { r = -r; }
    return r;
}


// One extra mad over fastAtan2_div2pi, although that is typically accurate enough.
//
// max error ~ 3.6957397769599165e-05
float fastAtan2_div2pi_accurate(float y, float x)
{
    float a = min(abs(x), abs(y)) / max(abs(x), abs(y));
    float s = a * a;
    float r = (((-0.0066609612639593 * s + 0.023972538405749075) * s + -0.05140823187987065) * s + -0.8409411267732256) * a + a;
    if(abs(y) > abs(x)) { r = 0.25 - r; }
    if(x < 0.0) { r = 0.5 - r; }
    r = multiplySign(r, y); // if(y < 0) { r = -r; }
    return r;
}


int triangleToQuadVertexIdCW(int vertexId)
{
    // 0---1
    // | \ |
    // 3---2
    //
    // 0 1 2 =>  0 1 2
    // 3 4 5 =>  2 3 0
    if(vertexId < 3) { return vertexId; }
    return (vertexId - 1) & 3;
}

int triangleToQuadVertexIdZ(int vertexId)
{
    // 0---1
    // | / |
    // 2---3
    //
    // 0 1 2 =>  0 1 2
    // 3 4 5 =>  1 2 3
    if(vertexId < 3) { return vertexId; }
    return vertexId - 2;
}


uint packR11G11B10(vec3 value)
{
    uint r = (packHalf2x16(vec2(value.x, 0.0)) << 17u) & 0xffe00000u;
    uint g = (packHalf2x16(vec2(value.y, 0.0)) << 6u) & 0x001ffc00u;
    uint b = (packHalf2x16(vec2(value.z, 0.0)) >> 5u) & 0x000003ffu;
    return r | g | b;
}


vec3 unpackR11G11B10(uint value)
{
    return vec3(
        unpackHalf2x16((value >> 17u) & 0x7ff0u).x,
        unpackHalf2x16((value >> 6u) & 0x7ff0u).x,
        unpackHalf2x16((value << 5u) & 0x7fe0u).x
    );
}

#endif
