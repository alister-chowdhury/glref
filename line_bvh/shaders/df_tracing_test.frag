#version 460 core

layout(binding=0) uniform sampler2D distanceField;
layout(location=0)  uniform vec2 targetUV;
layout(location=0) in vec2 uv;
layout(location=0) out vec4 col;


void main()
{

    // Trace from UV to target
#if 0
    vec2 toTarget = targetUV - uv;
    float dist = length(toTarget);
    vec2 ro = uv;
    vec2 rd = toTarget / dist;
    // Trace from target to UV
#else
    vec2 fromTarget = uv - targetUV;
    float dist = length(fromTarget);
    vec2 ro = targetUV;
    vec2 rd = fromTarget / dist;
#endif

    int numSamples = 0;
    bool visible = false;

    const int maxSteps = 1024;
    float bias = 0.5 / 1024.0; // hardcoding for now, should be (0.5 / dim)
    bias *= 64.0;


    // This should probably go up and down the mip chain based upon
    // the last distance

    int i=0;
    int mip=6;
    for(; mip>-1; --mip)
    {
        for(; i<maxSteps; ++i)
        {
            ++numSamples;
            float d = textureLod(distanceField, ro, float(mip)).x * 0.95;
            if(d < bias)
            {
                break;
            }

            ro += rd * d;
            dist -= d;
            if(dist <= 0)
            {
                visible = true;
                break;
            }
        }

        if(visible)
        {
            break;
        }

        bias *= 0.5;

    }

    float numVisits = float(numSamples) / float(8);
    float noHit = float(visible);
    float mipF = float(mip) / 6.0;
    col = vec4(numVisits, noHit, mipF, 1.);
    col = vec4(noHit, mipF, mipF, 1);
}

