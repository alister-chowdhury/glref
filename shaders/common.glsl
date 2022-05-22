#ifndef COMMON_GLSL_H
#define COMMON_GLSL_H

#define PI          3.141592653589793238462643383279502884197169399
#define HALFPI      1.5707963267948966192313216916397514420985847
#define TWOPI       6.283185307179586476925286766559005768394338799
#define INVPI       0.3183098861837906715377675267450287240689192915
#define INVTWOPI    0.1591549430918953357688837633725143620344596457
#define SQRT2       1.414213562373095048801688724209698078569671875
#define INVSQRT2    0.7071067811865475244008443621048490392848359377



// https://math.stackexchange.com/a/1105038
float fastAtan2(float y, float x)
{
    float a = min(abs(x), abs(y)) / max(abs(x), abs(y));
    float s = a * a;
    float r = ((-0.0464964749 * s + 0.15931422) * s - 0.327622764) * s * a + a;
    if(abs(y) > abs(x)) { r = HALFPI - r; }
    if(x < 0) { r = PI - r; }
    if(y < 0) { r = -r; }
    return r;
}


#endif
