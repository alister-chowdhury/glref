#version 460 core

layout(binding=0) uniform sampler2D anisoDistanceField;
layout(location=0)  uniform vec2 targetUV;
layout(location=0) in vec2 uv;
layout(location=0) out vec4 col;


vec4 getStepMask(vec2 rd)
{
    vec4 stepMask = vec4(0);
    
    if(abs(rd.x) > abs(rd.y))
    {
        if(rd.x < 0) { stepMask.x = 1.0; }
        else { stepMask.z = 1.0; }
    }
    else
    {
        if(rd.y > 0) { stepMask.y = 1.0; }
        else { stepMask.w = 1.0; }        
    }

    return stepMask;
}


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

    vec4 forwardMask = getStepMask(rd) * 0.9;
    vec4 backMask = forwardMask.zwxy;

    int numSamples = 0;
    bool visible = false;

    const int maxSteps = 10;
    const float bias = 1 / 512.0;
    float lastForward = 1e+35;

    // HAS LEAKING PROBLEMS!!!!
    // SADLY ITS LIKE OVER 3x FASTER THAN DF

    for(int i=0; i<maxSteps; ++i)
    {
        ++numSamples;
        vec4 DF = textureLod(anisoDistanceField, ro, 0);
        float d = dot(forwardMask, DF);
        float md = min(min(DF.x, DF.y), min(DF.z, DF.w));

        if(md < bias)
        {
            break;
        }

        if(abs(dot(backMask, DF) - lastForward) < bias)
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

        lastForward = d;
        // break;
    }

    float numVisits = float(numSamples) / float(8);
    float noHit = float(visible);
    col = vec4(numVisits, noHit, noHit, 1.);
}

