# This was a failed attempt at reconstructing triangles from a shadow map
# to create more defined edges (prehaps I'll eventually come back to it)


from math import cos, sin, pi, radians

import numpy

from OpenGL.GL import *

import viewport


SCENE_VERTEX_SHADER_SOURCE = """
#version 460 core

layout(location = 0) uniform mat4 model;
layout(location = 1) uniform mat4 modelViewProjection;
layout(location = 2) uniform mat4 inverseTransposeModel;

layout(location = 0) in vec3 P;
layout(location = 1) in vec3 N;

layout(location = 0) out vec3 outP;
layout(location = 1) out vec3 outN;

void main() {
    vec4 worldP = model * vec4(P, 1.0);
    outP = worldP.xyz / worldP.w;
    outN = (inverseTransposeModel * vec4(N, 1.0)).xyz;
    gl_Position = modelViewProjection * vec4(P, 1.0);
}
"""

SCENE_FRAGMENT_SHADER_SOURCE = """
#version 460 core

layout(location = 0) in vec3 P;
layout(location = 1) in vec3 N;

layout(location = 0) out vec3 outP;
layout(location = 1) out vec3 outN;

void main() {
    outP = P;
    outN = normalize(N);
}
"""

GENERATE_SHADOWMAP_VERTEX_SHADER = """
#version 460 core

layout(location = 0) uniform mat4 modelViewProjection;

layout(location = 0) in vec3 P;

void main() {
    gl_Position = modelViewProjection * vec4(P, 1.0);
}

"""

SCREEN_VERTEX_SHADER = """
#version 460 core

layout(location = 0) out vec2 screenUv;

void main()
{
    screenUv = vec2(
        float(gl_VertexID % 2),
        float(gl_VertexID / 2)
    );
    gl_Position = vec4(2.0 * screenUv - 1.0, 0.0, 1.0);
}
"""

SPOTLIGHT_LIGHTING_FRAGMENT_SHADER = """
#version 460 core

layout(location = 0) in vec2 screenUv;


layout(binding = 0) uniform sampler2D worldPosition;
layout(binding = 1) uniform sampler2D worldNormals;

layout(binding = 2) uniform sampler2D lightShadowMap;


layout(location = 0) uniform vec4 lightColIntensity;
layout(location = 1) uniform vec2 lightFovInnerOuter;
layout(location = 2) uniform mat4 lightViewPerspective;
layout(location = 3) uniform mat4 lightInversePerspective;
layout(location = 4) uniform mat4 lightInverseView;


layout(location = 0) out vec4 outRgba;


#define INV_SQRT2 0.70710678118654752440084436210484903928483594


const vec2 lightMapDims = vec2(textureSize(lightShadowMap, 0));
const vec2 invLightMapDims = 1.0 / vec2(textureSize(lightShadowMap, 0));



// Extract the light position directly from the inverseView matrix
const vec3 lightPos = vec3(
    lightInverseView[3][0],
    lightInverseView[3][1],
    lightInverseView[3][2]
);



vec3 sampleWorldSpaceFromShadowmap(vec2 uv)
{
    float depth = textureLod(lightShadowMap, uv, 0).r;

    vec4 clipSpaceP = vec4(
        uv * 2.0 - 1.0,
        depth * 2.0 - 1.0,
        1.0
    );

    vec4 viewSpaceP = lightInversePerspective * clipSpaceP;
    viewSpaceP /= viewSpaceP.w;
    return (lightInverseView * viewSpaceP).xyz;
}


vec2 getGradient(vec2 uv)
{
    float bottomLeft = textureLod(lightShadowMap, uv - invLightMapDims * INV_SQRT2, 0).r;
    float bottom = textureLod(lightShadowMap, uv - vec2(0, invLightMapDims.y), 0).r;
    float bottomRight = textureLod(lightShadowMap, uv - vec2(-INV_SQRT2, INV_SQRT2) * invLightMapDims, 0).r;
    float left = textureLod(lightShadowMap, uv - vec2(invLightMapDims.x, 0), 0).r;
    float center = textureLod(lightShadowMap, uv, 0).r;
    float right = textureLod(lightShadowMap, uv + invLightMapDims, 0).r;
    float topLeft = textureLod(lightShadowMap, uv + vec2(-INV_SQRT2, INV_SQRT2) * invLightMapDims, 0).r;
    float top = textureLod(lightShadowMap, uv + vec2(0, invLightMapDims.y), 0).r;
    float topRight = textureLod(lightShadowMap, uv + invLightMapDims * INV_SQRT2, 0).r;

    vec2 accum = (
        vec2(-INV_SQRT2) * abs(bottomLeft-center)
        + vec2(0, -1) * abs(bottom-center)
        + vec2(-INV_SQRT2, INV_SQRT2) * abs(bottomRight-center)
        + vec2(-1, 0) * abs(left-center)
        + vec2(1, 0) * abs(right-center)
        + vec2(INV_SQRT2) * abs(topLeft-center)
        + vec2(0, 1) * abs(top-center)
        + vec2(INV_SQRT2, -INV_SQRT2) * abs(topRight-center)
    );

    if(accum == vec2(0.0)) { return vec2(1.0, 0.0); }
    return normalize(accum);

}


// https://www.geogebra.org/m/pnhd3hpm
bool testLineTriangleIntersection(
    vec3 lineStart, vec3 lineEnd,
    vec3 A, vec3 B, vec3 C
) {
    
    // Plane normal
    const vec3 N = cross(B-A, C-A);

    const float denom = dot(lineEnd - lineStart, N);
    float t = dot(A - lineStart, N) / denom;

    if(
        denom == 0.0    // Line is coplanar
        || t < 0.0001        // Line intersects the plane before lineStart
        //|| t > 0.9999        // Line intersects the plane after lineEnd (not sure this is possible?)
    ) {
        return false;
    }

    const vec3 intersectionPoint = lineStart + t * (lineEnd - lineStart);

    const float UU = dot(B - A, B - A);
    const float UV = dot(B - A, C - A);
    const float UW = dot(B - A, intersectionPoint - A);
    const float VV = dot(C - A, C - A);
    const float VW = dot(C - A, intersectionPoint - A);

    const float invStdenom = 1.0 / (dot(UV, UV) - dot(UU, VV));

    const float S = invStdenom * (dot(UV, VW) - dot(VV, UW));
    const float T = invStdenom * (dot(UV, UW) - dot(UU, VW));

    return (
        (S >= -0.0001 && S <= 1.0001)
        && (T >= -0.0001 && T <= 1.0001)
        && ((S + T) >= -0.0001 && (S + T) <= 1.0001)
    );
}



bool testInShadow(vec3 P)
{
    vec4 lightMapPos = lightViewPerspective * vec4(P, 1.0);
    lightMapPos.xy = (lightMapPos.xy / lightMapPos.w) * 0.5 + 0.5;


    // If the actual point isn't mappable to the texture, we're going to say it's in shadow
    // as the spotlight wouldn't actually be able to illuminate the point.
    // Additionally, we would effectively zero out the value later due to the dot product
    // involved in feathering intensity.
    // But this prevents us from having to do any extra texture samples.
    if(
        (min(lightMapPos.x, lightMapPos.y) <= 0.0)
        || (max(lightMapPos.x, lightMapPos.y) >= 1.0))
    {
        return true;
    }


    #if 0
    // Reconstruct triangles based upon depth
    vec3 topLeft = sampleWorldSpaceFromShadowmap(lightMapPos.xy - invLightMapDims.xy);
    vec3 top = sampleWorldSpaceFromShadowmap(vec2(lightMapPos.x, lightMapPos.y - invLightMapDims.y));
    vec3 topRight = sampleWorldSpaceFromShadowmap(vec2(lightMapPos.x + invLightMapDims.x, lightMapPos.y - invLightMapDims.y));
    
    vec3 left = sampleWorldSpaceFromShadowmap(vec2(lightMapPos.x - invLightMapDims.x, lightMapPos.y));
    vec3 center = sampleWorldSpaceFromShadowmap(lightMapPos.xy);
    vec3 right = sampleWorldSpaceFromShadowmap(vec2(lightMapPos.x + invLightMapDims.x, lightMapPos.y));

    vec3 bottomLeft = sampleWorldSpaceFromShadowmap(vec2(lightMapPos.x - invLightMapDims.x, lightMapPos.y + invLightMapDims.y));
    vec3 bottom = sampleWorldSpaceFromShadowmap(vec2(lightMapPos.x, lightMapPos.y + invLightMapDims.y));
    vec3 bottomRight = sampleWorldSpaceFromShadowmap(lightMapPos.xy + invLightMapDims.xy);


    return (

        testLineTriangleIntersection(P, lightPos, top, left, center)
        || testLineTriangleIntersection(P, lightPos, bottom, left, center)
        || testLineTriangleIntersection(P, lightPos, top, right, center)
        || testLineTriangleIntersection(P, lightPos, bottom, left, center)

        /*
        || testLineTriangleIntersection(P, lightPos, topLeft, top, center)
        || testLineTriangleIntersection(P, lightPos, topLeft, left, center)
        || testLineTriangleIntersection(P, lightPos, topRight, top, center)
        || testLineTriangleIntersection(P, lightPos, topRight, right, center)
        || testLineTriangleIntersection(P, lightPos, bottomLeft, bottom, center)
        || testLineTriangleIntersection(P, lightPos, bottomLeft, left, center)
        || testLineTriangleIntersection(P, lightPos, bottomRight, bottom, center)
        || testLineTriangleIntersection(P, lightPos, bottomRight, right, center)
        */
    );

    #elif 0


    vec2 bottomLeftCoord = floor(lightMapPos.xy * lightMapDims) * invLightMapDims;
    vec2 topLeftCoord = bottomLeftCoord + vec2(0.0, invLightMapDims.y);
    vec2 bottomRightCoord = bottomLeftCoord + vec2(invLightMapDims.x, 0.0);
    vec2 topRightCoord = topLeftCoord + vec2(invLightMapDims.x, 0.0);
    vec2 centerCoord = (bottomLeftCoord + topRightCoord) * 0.5;

    vec3 BL = sampleWorldSpaceFromShadowmap(bottomLeftCoord);
    vec3 BR = sampleWorldSpaceFromShadowmap(bottomRightCoord);
    vec3 Ce = sampleWorldSpaceFromShadowmap(centerCoord);
    vec3 TL = sampleWorldSpaceFromShadowmap(topLeftCoord);
    vec3 TR = sampleWorldSpaceFromShadowmap(topRightCoord);


    return (
        testLineTriangleIntersection(P, lightPos, BL, Ce, BR)
        || testLineTriangleIntersection(P, lightPos, BL, Ce, TL)
        || testLineTriangleIntersection(P, lightPos, BR, Ce, TR)
        || testLineTriangleIntersection(P, lightPos, TL, Ce, TR)
    );


    #else

    vec2 upVec = getGradient(lightMapPos.xy) * invLightMapDims;
    vec2 downVec = upVec * -1;
    vec2 rightVec = upVec.yx * vec2(1, -1);
    vec2 leftVec = rightVec * -1;

    vec3 topLeft = sampleWorldSpaceFromShadowmap(lightMapPos.xy + vec2(leftVec.x, upVec.y) * INV_SQRT2 );
    vec3 top = sampleWorldSpaceFromShadowmap(lightMapPos.xy + upVec );
    vec3 topRight = sampleWorldSpaceFromShadowmap(lightMapPos.xy + vec2(rightVec.x, upVec.y) * INV_SQRT2 );
    vec3 left = sampleWorldSpaceFromShadowmap(lightMapPos.xy + leftVec );
    vec3 center = sampleWorldSpaceFromShadowmap(lightMapPos.xy);
    vec3 right = sampleWorldSpaceFromShadowmap(lightMapPos.xy + rightVec );
    vec3 bottomLeft = sampleWorldSpaceFromShadowmap(lightMapPos.xy + vec2(leftVec.x, downVec.y) * INV_SQRT2 );
    vec3 bottom = sampleWorldSpaceFromShadowmap(lightMapPos.xy + downVec );
    vec3 bottomRight = sampleWorldSpaceFromShadowmap(lightMapPos.xy + vec2(rightVec.x, downVec.y) * INV_SQRT2 );


    return (
        testLineTriangleIntersection(P, lightPos, top, left, center)
        || testLineTriangleIntersection(P, lightPos, bottom, left, center)
        || testLineTriangleIntersection(P, lightPos, top, right, center)
        || testLineTriangleIntersection(P, lightPos, bottom, left, center)

        /*
        || testLineTriangleIntersection(P, lightPos, topLeft, top, center)
        || testLineTriangleIntersection(P, lightPos, topLeft, left, center)
        || testLineTriangleIntersection(P, lightPos, topRight, top, center)
        || testLineTriangleIntersection(P, lightPos, topRight, right, center)
        || testLineTriangleIntersection(P, lightPos, bottomLeft, bottom, center)
        || testLineTriangleIntersection(P, lightPos, bottomLeft, left, center)
        || testLineTriangleIntersection(P, lightPos, bottomRight, bottom, center)
        || testLineTriangleIntersection(P, lightPos, bottomRight, right, center)
        */
    );


    #endif
}


void main()
{

    vec3 P = textureLod(worldPosition, screenUv, 0).xyz;
    float intensity = 0.0;

    if(!testInShadow(P))
    {
        vec3 N = textureLod(worldNormals, screenUv, 0).xyz;
        float lamb = max(0, dot(N, normalize(lightPos-P)));

        // Need to fix to use the cone properly.
        intensity = lightColIntensity.w * clamp(
            (lamb - lightFovInnerOuter.x) / ( lightFovInnerOuter.y - lightFovInnerOuter.x ),
            0, 1
        );

        intensity = lightColIntensity.w * clamp(lamb, 0, 1);
    }

    outRgba = vec4(lightColIntensity.xyz * intensity, 1.0);
}


"""



class Renderer(object):


    def __init__(self):

        self.window = viewport.Window()
        self.camera = viewport.Camera()

        self.spotlight = viewport.Camera()

        self.window.on_init = self._init
        self.window.on_draw = self._draw
        self.window.on_resize = self._resize
        self.window.on_drag = self._drag
        self.window.on_keypress = self._keypress

        self.target_camera = self.camera


    def run(self):
        self.window.run()
    
    def _init(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        self._vao_ptr = ctypes.c_int()
        glCreateVertexArrays(1, self._vao_ptr)
        self._dummy_vao = self._vao_ptr.value

        self.plane = viewport.StaticGeometry(
            (3, 3, 2),
            viewport.PLANE_INDICES,
            viewport.PNUV_PLANE_VERTICES,
        )
        self._plane1_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 1],
        ], dtype=numpy.float32)

        self._plane2_model = numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0.1],
        ], dtype=numpy.float32)

        self._draw_scene_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=SCENE_VERTEX_SHADER_SOURCE,
            GL_FRAGMENT_SHADER=SCENE_FRAGMENT_SHADER_SOURCE
        )
        self._draw_shadowmap_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=GENERATE_SHADOWMAP_VERTEX_SHADER,
        )
        self._draw_spotlight_program = viewport.generate_shader_program(
            GL_VERTEX_SHADER=SCREEN_VERTEX_SHADER,
            GL_FRAGMENT_SHADER=SPOTLIGHT_LIGHTING_FRAGMENT_SHADER
        )

        self._scene_framebuffer_p = viewport.FramebufferTarget(
            GL_RGB32F, True,
        )
        self._scene_framebuffer_n = viewport.FramebufferTarget(
            GL_RGB32F, True,
        )
        self._scene_framebuffer_depth = viewport.FramebufferTarget(GL_DEPTH_STENCIL, False)
        self._framebuffer = viewport.Framebuffer(
            (self._scene_framebuffer_p, self._scene_framebuffer_n, self._scene_framebuffer_depth),
            wnd.width,
            wnd.height
        )

        self._light_shadow_depth = viewport.FramebufferTarget(
            GL_DEPTH_COMPONENT32F,
            True,
            # PCF friendly settings
            custom_texture_settings={
                GL_TEXTURE_WRAP_S: GL_REPEAT,
                GL_TEXTURE_WRAP_T: GL_CLAMP_TO_EDGE,
                GL_TEXTURE_MIN_FILTER: GL_LINEAR,
                GL_TEXTURE_MAG_FILTER: GL_LINEAR,
                GL_TEXTURE_COMPARE_FUNC: GL_LEQUAL,
                GL_TEXTURE_COMPARE_MODE: GL_COMPARE_REF_TO_TEXTURE,
            }
        )
        self._light_shadow_framebuffer = viewport.Framebuffer(
            (self._light_shadow_depth,),
            512, 512
        )

        self.camera.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )

        self.spotlight.look_at(
            numpy.array([0, 0, 0]),
            numpy.array([5, 10, 5]),
        )

        glViewport(0, 0, wnd.width, wnd.height)


    def _generate_shadow_map(self):
        previous_viewport = glGetIntegerv(GL_VIEWPORT)
        with self._light_shadow_framebuffer.bind():
            glClear(GL_DEPTH_BUFFER_BIT)
            glViewport(0, 0, 512, 512)
            glUseProgram(self._draw_shadowmap_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, (self._plane1_model * self.spotlight.view_projection).flatten())
            self.plane.draw()
            glUniformMatrix4fv(0, 1, GL_FALSE, (self._plane2_model * self.spotlight.view_projection).flatten())
            self.plane.draw()
        glViewport(
            previous_viewport[0],
            previous_viewport[1],
            previous_viewport[2],
            previous_viewport[3]
        )



    def _draw(self, wnd):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._generate_shadow_map()

        # Record a stencil on the framebuffer
        glEnable(GL_STENCIL_TEST)
        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
        glStencilMask(0xFF)

        # Draw the scene to the framebuffer
        with self._framebuffer.bind():
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            glUseProgram(self._draw_scene_program)
            glUniformMatrix4fv(0, 1, GL_FALSE, self._plane1_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._plane1_model * self.camera.view_projection).flatten())
            glUniformMatrix4fv(2, 1, GL_FALSE, self._plane1_model.T.I.flatten())
            self.plane.draw()
            glUniformMatrix4fv(0, 1, GL_FALSE, self._plane2_model.flatten())
            glUniformMatrix4fv(1, 1, GL_FALSE, (self._plane2_model * self.camera.view_projection).flatten())
            glUniformMatrix4fv(2, 1, GL_FALSE, self._plane2_model.T.I.flatten())
            self.plane.draw()

        glClearColor(1.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        # Copy the framebuffers stencil and use it as a mask
        self._framebuffer.blit_to_back(
            wnd.width,
            wnd.height,
            GL_STENCIL_BUFFER_BIT,
            GL_NEAREST
        )
        glDepthMask(GL_TRUE)
        glStencilFunc(GL_EQUAL, 1, 0xFF)
        glStencilMask(0x00)

        glUseProgram(self._draw_spotlight_program)
        glBindTextureUnit(0, self._scene_framebuffer_p.texture)
        glBindTextureUnit(1, self._scene_framebuffer_n.texture)
        glBindTextureUnit(2, self._light_shadow_depth.texture)
        glUniform4f(0, 1, 1, 1, 1)                                                   # lightColIntensity
        glUniform2f(1, radians(self.spotlight.fov)*0.5, radians(self.spotlight.fov)) # lightFovInnerOuter
        glUniformMatrix4fv(2, 1, GL_FALSE, self.spotlight.view_projection.flatten())
        glUniformMatrix4fv(3, 1, GL_FALSE, self.spotlight.projection.I.flatten())
        glUniformMatrix4fv(4, 1, GL_FALSE, self.spotlight.view.I.flatten())

        glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)
        glBindVertexArray(self._dummy_vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glDepthMask(GL_TRUE)
        glEnable(GL_DEPTH_TEST)

        glDisable(GL_STENCIL_TEST)

    def _resize(self, wnd, width, height):
        self._framebuffer.resize(width, height)
        glViewport(0, 0, width, height)
        self.camera.set_aspect(width/height)

    def _keypress(self, wnd, key, x, y):
        # Move the camera
        if key == b'w':
            self.target_camera.move_local(numpy.array([0, 0, 1]))
        elif key == b's':
            self.target_camera.move_local(numpy.array([0, 0, -1]))

        elif key == b'a':
            self.target_camera.move_local(numpy.array([1, 0, 0]))
        elif key == b'd':
            self.target_camera.move_local(numpy.array([-1, 0, 0]))

        elif key == b'q':
            self.target_camera.move_local(numpy.array([0, 1, 0]))
        elif key == b'e':
            self.target_camera.move_local(numpy.array([0, -1, 0]))

        elif key == b'c':
            self.target_camera = (
                self.camera
                if self.target_camera != self.camera
                else self.spotlight
            )

        # Wireframe / Solid etc
        elif key == b'1':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif key == b'2':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # No redraw
        else:
            return

        wnd.redraw()

    def _drag(self, wnd, x, y, button):
        deriv_u = x / wnd.width
        deriv_v = y / wnd.height

        sin_u = sin(deriv_u * pi)
        cos_u = cos(deriv_u * pi)
        sin_v = sin(deriv_v * pi)
        cos_v = cos(deriv_v * pi)

        ortho = self.target_camera.orthonormal_basis
        
        # Y
        M = numpy.matrix([
            [cos_u, 0, sin_u],
            [0, 1, 0],
            [-sin_u, 0, cos_u],
        ])

        # XY stuff
        if button == wnd.RIGHT:
            N = numpy.matrix([
                [cos_v, -sin_v, 0],
                [sin_v, cos_v, 0],
                [0, 0, 1],
            ])
        else:
            N = numpy.matrix([
                [1, 0, 0],
                [0, cos_v, -sin_v],
                [0, sin_v, cos_v],
            ])
        N = ortho * N * ortho.I
        M *= N

        self.target_camera.append_3x3_transform(M)

        wnd.redraw()


if __name__ == "__main__":
    Renderer().run()

