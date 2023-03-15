#version 460 core

#include "../../shaders/common.glsl"
#include "df_tracing.glsli"


#ifndef PROBE_WIDTH
#define PROBE_WIDTH 4
#endif // PROBE_WIDTH

#ifndef PROBE_HEIGHT
#define PROBE_HEIGHT 4
#endif // PROBE_WIDTH


layout(location=1) uniform vec4 probeSizeAndInvSize;

layout(location=0) in vec2 uv;

layout(location=0) out vec3 sampledData;


void main()
{
    vec2 probeDim = vec2(PROBE_WIDTH, PROBE_HEIGHT);
    int probePixelIndex = ((int(gl_FragCoord.y) % PROBE_HEIGHT) * PROBE_WIDTH)
                          + int(gl_FragCoord.x) % PROBE_WIDTH
                          ;
    vec2 probeUV = (floor(uv * probeSizeAndInvSize.xy) + 0.5) * probeSizeAndInvSize.zw;

    float probeAngle = float(probePixelIndex) / float(PROBE_WIDTH * PROBE_HEIGHT) * TWOPI;
    vec2 probeDir = vec2(cos(probeAngle), sin(probeAngle));


    vec3 radiance = vec3(0);

    // Should have a linked light list here, but for now I'll just hardcode things.
    // and should save a bitmask of visible lights, rather than sampling them over
    // and over.
    // Also pretty sure, we "should" be able to convolve multiple lightings into a
    // spherical harominic, without needing to actually create N x N pixels like this.
    // Presumably, we can do like MakeSHFromLight(...) and sum the results?

    // Directional light
    {
        vec2 dirLightN = normalize(vec2(-1, 0.5));
        vec3 lightIntensity = vec3(0.9, 0.1, 1.0);
        if(df_trace(probeUV, -dirLightN, 2.0).visible)
        {
            radiance += max(0.0, -dot(dirLightN, probeDir)) * lightIntensity;
        }
    }


    // Point lights
    {
        vec2 pointLightPos = vec2(0.3555, 0.5606);
        vec3 lightIntensity = vec3(0.9, 0.5, 0.1);
        vec2 toLight = pointLightPos - uv;
        float toLightDist = length(toLight);
        toLight /= toLightDist;
        if(df_trace(probeUV, toLight, toLightDist).visible)
        {
            radiance += max(0.0, -dot(toLight, probeDir)) * lightIntensity * 1.0 / (100.0 * toLightDist * toLightDist + 1.0);
        }
    }


    {
        vec2 pointLightPos = vec2(0.2598, 0.8418);
        vec3 lightIntensity = vec3(0.1, 0.9, 0.3);
        vec2 toLight = pointLightPos - uv;
        float toLightDist = length(toLight);
        toLight /= toLightDist;
        if(df_trace(probeUV, toLight, toLightDist).visible)
        {
            radiance += max(0.0, -dot(toLight, probeDir)) * lightIntensity * 1.0 / (100.0 * toLightDist * toLightDist + 1.0);
        }
    }

    {
        vec2 pointLightPos = vec2(0.666, 0.1309);
        vec3 lightIntensity = vec3(0.1, 0.2, 0.8);
        vec2 toLight = pointLightPos - uv;
        float toLightDist = length(toLight);
        toLight /= toLightDist;
        if(df_trace(probeUV, toLight, toLightDist).visible)
        {
            radiance += max(0.0, -dot(toLight, probeDir)) * lightIntensity * 1.0 / (100.0 * toLightDist * toLightDist + 1.0);
        }
    }


    {
        vec2 pointLightPos = vec2(0.1426, 0.2344);
        vec3 lightIntensity = vec3(0.95, 0.0, 0.3);
        vec2 toLight = pointLightPos - uv;
        float toLightDist = length(toLight);
        toLight /= toLightDist;
        if(df_trace(probeUV, toLight, toLightDist).visible)
        {
            radiance += max(0.0, -dot(toLight, probeDir)) * lightIntensity * 1.0 / (100.0 * toLightDist * toLightDist + 1.0);
        }
    }

    sampledData = radiance;
}
