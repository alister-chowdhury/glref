#version 460 core

#include "../../../shaders/common.glsl"

#if USE_LINE_BVH
#include "../v1_tracing.glsli"
#else // USE_LINE_BVH
#include "../df_tracing.glsli"
#endif // USE_LINE_BVH
#include "../ch_common.glsli"


layout(location=0) in vec2 uv;
layout(location=1) in vec2 innerNDC;

layout(location=1) uniform vec4 probeSizeAndInvSize;

layout(binding=1) uniform sampler2D inRGBSH0;
layout(binding=2) uniform sampler2D inRGBSH1;
layout(binding=3) uniform sampler2D inRGBSH2;

layout(location=0) out vec4 outCol;


void accumIfVisible(vec2 ro,
                    vec2 cornerUv,
                    float weight,
                    inout CH2 CHR,
                    inout CH2 CHG,
                    inout CH2 CHB,
                    inout float totalWeight)
{
    vec2 duv = cornerUv - ro;
    float l = length(duv);
#if USE_LINE_BVH
    if(traceLineBvhV1(ro, duv, 1.0, true).hitLineId == 0xffffffffu)
#else
    if(df_trace(uv, duv / l, l).visible)
#endif
    {
        totalWeight += weight;
        ivec2 coord = ivec2(cornerUv * probeSizeAndInvSize.xy);
        vec3 RGBSH0 = texelFetch(inRGBSH0, coord, 0).xyz;
        vec4 RGBSH1 = texelFetch(inRGBSH1, coord, 0).xyzw;
        vec2 RGBSH2 = texelFetch(inRGBSH2, coord, 0).xy;
        CHR.V += vec3(RGBSH0.x, RGBSH1.xy) * weight;
        CHG.V += vec3(RGBSH0.y, RGBSH1.zw) * weight;
        CHB.V += vec3(RGBSH0.z, RGBSH2.xy) * weight;
    }
}

void main()
{
    float d = dot(innerNDC, innerNDC);
    if(d >= 1.0)
    {
        discard;
    }

    vec2 uv2 = uv - probeSizeAndInvSize.zw * 0.5;

#if USE_LINE_BVH
    uv2 = uv;
#endif // USE_LINE_BVH

    vec2 shNormal = normalize(vec3(innerNDC, sqrt(1.0 - d))).xy;
    vec2 probeCorner = probeSizeAndInvSize.xy * uv2;
    vec2 interp = fract(probeCorner);
    vec2 probeCorner00 = (floor(probeCorner) - 0.5) * probeSizeAndInvSize.zw;
    vec2 probeCorner01 = (floor(probeCorner) + 0.0) * probeSizeAndInvSize.zw;

    CH2 CHR;
    CH2 CHG;
    CH2 CHB;

    // Need to bias both +0.5 and -0.5 to work?
    // still has weird streaking artefacts
    float totalWeight = 0;
    // accumIfVisible(uv, probeCorner00, (1.0 - interp.x) * (1.0 - interp.y), CHR, CHG, CHB, totalWeight);
    // accumIfVisible(uv, probeCorner00 + vec2(probeSizeAndInvSize.z, 0), interp.x * (1.0 - interp.y), CHR, CHG, CHB, totalWeight);
    // accumIfVisible(uv, probeCorner00 + vec2(0, probeSizeAndInvSize.w), (1.0 - interp.x) * interp.y, CHR, CHG, CHB, totalWeight);
    // accumIfVisible(uv, probeCorner00 + probeSizeAndInvSize.zw, interp.x * interp.y, CHR, CHG, CHB, totalWeight);
    accumIfVisible(uv2, probeCorner01, (1.0 - interp.x) * (1.0 - interp.y), CHR, CHG, CHB, totalWeight);
    accumIfVisible(uv2, probeCorner01 + vec2(probeSizeAndInvSize.z, 0), interp.x * (1.0 - interp.y), CHR, CHG, CHB, totalWeight);
    accumIfVisible(uv2, probeCorner01 + vec2(0, probeSizeAndInvSize.w), (1.0 - interp.x) * interp.y, CHR, CHG, CHB, totalWeight);
    accumIfVisible(uv2, probeCorner01 + probeSizeAndInvSize.zw, interp.x * interp.y, CHR, CHG, CHB, totalWeight);


    vec3 value = vec3(1.0, 0.0,1.0);
    if(totalWeight > 0.0)
    {
        totalWeight = 1.0 / totalWeight;
        CHR.V *= totalWeight;
        CHG.V *= totalWeight;
        CHB.V *= totalWeight;

#if 1
        value = vec3(
            max(0., CH2RadianceEval(CHR, shNormal)),
            max(0., CH2RadianceEval(CHG, shNormal)),
            max(0., CH2RadianceEval(CHB, shNormal))
        ) * 50.0;
#elif 1
        CH2 evalBasis = CH2Basis(-shNormal);
        value = vec3(
            max(0., dot(CHR.V, evalBasis.V)),
            max(0., dot(CHG.V, evalBasis.V)),
            max(0., dot(CHB.V, evalBasis.V))
        ) * 10.0;
#elif 1
        CH2 evalBasis = CH2DiffuseTransfer(-shNormal);
        value = vec3(
            max(0., dot(CHR.V, evalBasis.V)),
            max(0., dot(CHG.V, evalBasis.V)),
            max(0., dot(CHB.V, evalBasis.V))
        ) * 10.0;
#else
        value = vec3(CHR.V.x, CHG.V.x, CHB.V.x) * 10.0;
#endif
    }

    outCol = vec4(value, 1.0);

}
