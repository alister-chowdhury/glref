#version 460 core


layout(location=0) out float v;

void main()
{
    vec2 ndc;
    
    switch(gl_VertexID & 3)
    {
        case 0: { ndc = vec2(-4, -1); break; }
        case 1: { ndc = vec2(1, -1); break; }
        case 2: { ndc = vec2(1, 4); break; }
    }

    v = ndc.y * 0.5 + 0.5;
    gl_Position = vec4(ndc, 0., 1.);
}
