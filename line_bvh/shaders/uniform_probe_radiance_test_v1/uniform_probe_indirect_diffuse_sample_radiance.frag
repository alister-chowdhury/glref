#version 460 core

#include "../../../shaders/common.glsl"
#include "../ch_common.glsli"


// TODO: Do a line intersection instead store the distance,
//       but also store a normal (polar coordinates), which
//       should be used to evaluate the radiance probes (and
//       the irradiance probes once that seems to work)



layout(location=0) in vec2 uv;

layout(binding=0) uniform usampler2D visibilityDistances;
layout(binding=1) uniform sampler2D inRGBSH0;
layout(binding=2) uniform sampler2D inRGBSH1;
layout(binding=3) uniform sampler2D inRGBSH2;

layout(location=0) out vec3  outRGBSH0;
layout(location=1) out vec4  outRGBSH1;
layout(location=2) out vec2  outRGBSH2;


vec4 unpackVisibilityDistances(uint a)
{
    return vec4(
        float(a & 0xff),
        float((a >> 8) & 0xff),
        float((a >> 16) & 0xff),
        float(a >> 24)
    ) * (1.0 / 255.0);
}


void accum(float index, float distance, inout CH2 R, inout CH2 G, inout CH2 B)
{
    // TODO: Add golden ratio jitter based upon the probe index
    float probeAngle = index / 16.0 * TWOPI;
    vec2 probeDir = vec2(cos(probeAngle), sin(probeAngle));
    vec2 targetUv = uv + probeDir * distance;

    vec3 RGBSH0 = texture(inRGBSH0, targetUv).xyz;
    vec4 RGBSH1 = texture(inRGBSH1, targetUv).xyzw;
    vec2 RGBSH2 = texture(inRGBSH2, targetUv).xy;

    CH2 inR; inR.V = vec3(RGBSH0.x, RGBSH1.xy);
    CH2 inG; inG.V = vec3(RGBSH0.y, RGBSH1.zw);
    CH2 inB; inB.V = vec3(RGBSH0.z, RGBSH2.xy);

#if 0
    vec3 radiance = vec3(
        max(0., CH2RadianceEval(inR, probeDir)),
        max(0., CH2RadianceEval(inG, probeDir)),
        max(0., CH2RadianceEval(inB, probeDir))
    );
#else
    CH2 evalBasis = CH2Basis(-probeDir);
    vec3 radiance = vec3(
        max(0., dot(inR.V, evalBasis.V)),
        max(0., dot(inG.V, evalBasis.V)),
        max(0., dot(inB.V, evalBasis.V))
    );

#endif
    CH2 basis = CH2Mul(CH2Basis(-probeDir), 1.0/16.0);
    R = CH2Add(R, CH2Mul(basis, radiance.x));
    G = CH2Add(G, CH2Mul(basis, radiance.g));
    B = CH2Add(B, CH2Mul(basis, radiance.b));
}


void main()
{
    uvec4 distancesRaw  = texelFetch(visibilityDistances, ivec2(gl_FragCoord.xy), 0);

    CH2 accumR;
    CH2 accumG;
    CH2 accumB;

    vec4 distances0_3   = unpackVisibilityDistances(distancesRaw.x);
    accum(0, distances0_3.x, accumR, accumG, accumB);
    accum(1, distances0_3.y, accumR, accumG, accumB);
    accum(2, distances0_3.z, accumR, accumG, accumB);
    accum(3, distances0_3.w, accumR, accumG, accumB);

    vec4 distances4_7   = unpackVisibilityDistances(distancesRaw.y);
    accum(0, distances4_7.x, accumR, accumG, accumB);
    accum(1, distances4_7.y, accumR, accumG, accumB);
    accum(2, distances4_7.z, accumR, accumG, accumB);
    accum(3, distances4_7.w, accumR, accumG, accumB);

    vec4 distances8_11  = unpackVisibilityDistances(distancesRaw.z);
    accum(0, distances8_11.x, accumR, accumG, accumB);
    accum(1, distances8_11.y, accumR, accumG, accumB);
    accum(2, distances8_11.z, accumR, accumG, accumB);
    accum(3, distances8_11.w, accumR, accumG, accumB);

    vec4 distances12_15 = unpackVisibilityDistances(distancesRaw.w);
    accum(0, distances12_15.x, accumR, accumG, accumB);
    accum(1, distances12_15.y, accumR, accumG, accumB);
    accum(2, distances12_15.z, accumR, accumG, accumB);
    accum(3, distances12_15.w, accumR, accumG, accumB);

    outRGBSH0 = vec3(accumR.V.x, accumG.V.x, accumB.V.x);
    outRGBSH1 = vec4(accumR.V.yz, accumG.V.yz);
    outRGBSH2 = accumB.V.yz;
}
