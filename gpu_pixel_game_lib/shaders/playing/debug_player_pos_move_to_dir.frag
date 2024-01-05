#version 460 core


layout(location=0) in vec2 P;
layout(location=0) out vec4 outCol;


float cross2D(vec2 A, vec2 B) { return A.x * B.y - A.y * B.x; }


float triangleSDF(vec2 inP)
{
    vec2 uv = inP + vec2(0.5, 0.0);
    float S = float((1.0 - uv.x) > abs(uv.y) && (uv.x >= 0.0));
    return S;
}

void main()
{
    float mask = triangleSDF(P);
    outCol = vec4(mask);
}
