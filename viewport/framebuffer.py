import ctypes
from contextlib import contextmanager

import numpy

from OpenGL.GL import *


class FramebufferTarget(object):

    def __init__(self, pixel_type, make_texture, custom_texture_settings=None):
        self._intitialized = False
        self.pixel_type = pixel_type
        self.make_texture = make_texture
        self._ptr = ctypes.c_int()

        self.is_depth = self.pixel_type in (
            GL_DEPTH_COMPONENT,
            GL_DEPTH_COMPONENT32F,
            GL_DEPTH_COMPONENT24,
            GL_DEPTH_COMPONENT16,
        )
        self.is_stencil = self.pixel_type in (
            GL_STENCIL_INDEX,
            GL_STENCIL_INDEX8,
        )
        self.is_depth_stencil = self.pixel_type in (
            GL_DEPTH_STENCIL,
            GL_DEPTH32F_STENCIL8,
            GL_DEPTH24_STENCIL8,
        )

        self.custom_texture_settings = custom_texture_settings

        # Auto fixup pixel types for depth/stencil if we're writing it to
        # a texture.
        if make_texture and (self.is_depth or self.is_stencil or self.is_depth_stencil):
            if self.is_depth and pixel_type == GL_DEPTH_COMPONENT:
                self.pixel_type = GL_DEPTH_COMPONENT24
            elif self.is_stencil and pixel_type == GL_STENCIL_INDEX:
                self.pixel_type = GL_STENCIL_INDEX8
            elif self.is_depth_stencil and pixel_type == GL_DEPTH_STENCIL:
                self.pixel_type = GL_DEPTH24_STENCIL8

        self._attachment_id = None
        self._width = 0
        self._height = 0

    def __del__(self):
        self._destroy()

    def _set_attachment_id(self, idx):
        if self._attachment_id is not None:
            raise RuntimeError(
                "FramebufferTarget already attached to a Framebuffer"
            )
        self._attachment_id = idx

    def _destroy(self):
        if self._intitialized:
            if self.make_texture:
                glDeleteTextures(1, self._ptr)
            else:
                glDeleteRenderbuffers(1, self._ptr)
            self._intitialized = False

    def _create(self, framebuffer, width, height):
        self._destroy()
        self._width = width
        self._height = height
        if self.make_texture:
            glCreateTextures(GL_TEXTURE_2D, 1, self._ptr)
            glTextureStorage2D(self.value, 1, self.pixel_type, width, height)

            if self.custom_texture_settings:
                for pname, pvalue in self.custom_texture_settings.items():
                    glTextureParameteri(self.value, pname, pvalue)
            else:
                glTextureParameteri(self.value, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                glTextureParameteri(self.value, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                glTextureParameteri(self.value, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTextureParameteri(self.value, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glNamedFramebufferTexture(framebuffer, self._attachment_id, self.value, 0)
        else:
            glGenRenderbuffers(1, self._ptr)
            glNamedRenderbufferStorage(self.value, self.pixel_type, width, height)
            glNamedFramebufferRenderbuffer(framebuffer, self._attachment_id, GL_RENDERBUFFER, self.value)

        self._intitialized = True

    @property
    def value(self):
        return self._ptr.value

    @property
    def texture(self):
        if not self.make_texture:
            return None
        return self._ptr.value


class ProxyFramebufferTarget(object):
    """Proxy framebuffer target, must be used AFTER the source has been initialized / resized."""

    def __init__(self, target):
        self._target = target
        self._attachment_id = None

    def _set_attachment_id(self, idx):
        if self._attachment_id is not None:
            raise RuntimeError(
                "ProxyFramebufferTarget already attached to a Framebuffer"
            )
        self._attachment_id = idx

    def _create(self, framebuffer, width, height):
        if width != self._target._width and height != self._target._height:
            raise RuntimeError(
                "ProxyFramebufferTarget width/height don't match source FramebufferTarget"
            )
        if self.make_texture:
            glNamedFramebufferTexture(framebuffer, self._attachment_id, self.value, 0)
        else:
            glNamedFramebufferRenderbuffer(framebuffer, self._attachment_id, GL_RENDERBUFFER, self.value)

    @property
    def pixel_type(self):
        return self._target.pixel_type

    @property
    def make_texture(self):
        return self._target.make_texture

    @property
    def is_depth(self):
        return self._target.is_depth

    @property
    def is_stencil(self):
        return self._target.is_stencil

    @property
    def is_depth_stencil(self):
        return self._target.is_depth_stencil

    @property
    def custom_texture_settings(self):
        return self._target.custom_texture_settings

    @property
    def value(self):
        return self._target.value

    @property
    def texture(self):
        return self._target.texture


class CubemapFramebufferTarget(FramebufferTarget):

    def __init__(self, pixel_type, custom_texture_settings=None):
        super(CubemapFramebufferTarget, self).__init__(
            pixel_type=pixel_type,
            make_texture=True,
            custom_texture_settings=custom_texture_settings)
        self._bound_layer = None

    def _create(self, framebuffer, width, height):
        self._destroy()
        glCreateTextures(GL_TEXTURE_CUBE_MAP, 1, self._ptr)
        glTextureStorage2D(self.value, 1, self.pixel_type, width, height)

        if self.custom_texture_settings:
            for pname, pvalue in self.custom_texture_settings.items():
                glTextureParameteri(self.value, pname, pvalue)
        else:
            glTextureParameteri(self.value, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTextureParameteri(self.value, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTextureParameteri(self.value, GL_TEXTURE_WRAP_R, GL_REPEAT)
            glTextureParameteri(self.value, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTextureParameteri(self.value, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glNamedFramebufferTexture(framebuffer, self._attachment_id, self.value, 0)
        self._intitialized = True

    def _bind_layer(self, framebuffer, layer):
        if self._bound_layer != layer:
            # This doesn't seem to work correct with (atleast my) Intel driver, throwing an invalid
            # operation.
            if 0:
                glNamedFramebufferTextureLayer(framebuffer, self._attachment_id, self.value, 0, layer)
            
            # falling back to old GL
            else:
                glFramebufferTexture2D(
                    GL_FRAMEBUFFER,
                    self._attachment_id,
                    GL_TEXTURE_CUBE_MAP_POSITIVE_X+layer,
                    self.value,
                    0
                )

        self._bound_layer 

    def _bind(self, framebuffer, layer=None):
        if layer is not None:
            self._bind_layer(framebuffer, layer)
        elif self._bound_layer is not None:
            glNamedFramebufferTexture(framebuffer, self._attachment_id, self.value, 0)
            self._bound_layer = None


class Framebuffer(object):

    def __init__(self, render_targets, width, height):
        # Setup attachment ids
        self._intitialized = False

        colour_id = GL_COLOR_ATTACHMENT0
        self._colour_attachments = []
        self._render_targets = render_targets

        for render_target in render_targets:
            if render_target.is_depth:
                render_target._set_attachment_id(GL_DEPTH_ATTACHMENT)
            elif render_target.is_stencil:
                render_target._set_attachment_id(GL_STENCIL_ATTACHMENT)
            elif render_target.is_depth_stencil:
                render_target._set_attachment_id(GL_DEPTH_STENCIL_ATTACHMENT)
            else:
                render_target._set_attachment_id(colour_id)
                self._colour_attachments.append(colour_id)
                colour_id = colour_id + 1

        self._framebuffer_ptr = ctypes.c_int()
        self._create(width, height)

    @contextmanager
    def bind(self):
        """Bind the framebuffer to be drawn too."""
        glBindFramebuffer(GL_FRAMEBUFFER, self.value)
        glDrawBuffers(len(self._colour_attachments), self._colour_attachments)
        yield
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glDrawBuffer(GL_BACK)

    def resize(self, width, height):
        """Resize the frame buffer."""
        self._create(width, height)

    @property
    def value(self):
        return self._framebuffer_ptr.value

    def __del__(self):
        self._destroy()

    def _destroy(self):
        if self._intitialized:
            glDeleteFramebuffers(1, self._framebuffer_ptr)
            self._intitialized = False

    def _create(self, width, height):
        self._destroy()
        glCreateFramebuffers(1, self._framebuffer_ptr)
        framebuffer = self._framebuffer_ptr.value

        for render_target in self._render_targets:
            render_target._create(framebuffer, width, height)

        # Always check that our framebuffer is ok
        if(glCheckNamedFramebufferStatus(framebuffer, GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE):
            print("Framebuffer fail")
            exit(-1)

        self._intitialized = True

    def blit_to_back(self, width, height, mask=GL_COLOR_BUFFER_BIT, filter_=GL_LINEAR):
        glBlitNamedFramebuffer(
            self.value,
            0,  # GL_BACK
            0, 0, width, height,
            0, 0, width, height,
            mask,
            filter_
        )

    def blit(self, target, width, height, mask=GL_COLOR_BUFFER_BIT, filter_=GL_LINEAR):
        glBlitNamedFramebuffer(
            self.value,
            target,
            0, 0, width, height,
            0, 0, width, height,
            mask,
            filter_
        )


class CubemapFramebuffer(Framebuffer):

    @contextmanager
    def bind(self, layer=None):
        """Bind the framebuffer to be drawn too."""
        glBindFramebuffer(GL_FRAMEBUFFER, self.value)
        for render_target in self._render_targets:
            render_target._bind(self.value, layer)
        glDrawBuffers(len(self._colour_attachments), self._colour_attachments)
        yield
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glDrawBuffer(GL_BACK)


class WrappedFramebuffer(object):
    """Wrapper around existing textures, for finer control over things like mips."""

    def __init__(self):
        self._built = False
        self._next_colour_id = GL_COLOR_ATTACHMENT0
        self._used_attachment_ids = []
        self._intitialized = False
        self._framebuffer_ptr = ctypes.c_int()
        self._framebuffer = None
        self._create()

    def __del__(self):
        self._destroy()

    def add_col_attachment(self, texture, mip=0):
        colour_id = self._next_colour_id
        self._next_colour_id += 1
        self._add(texture, mip, colour_id)
        return self

    def add_depth_stencil(self, texture, mip=0):
        self._add(texture, mip, GL_DEPTH_STENCIL_ATTACHMENT)
        return self

    def add_depth(self, texture, mip=0):
        self._add(texture, mip, GL_DEPTH_ATTACHMENT)
        return self

    def add_stencil(self, texture, mip=0):
        self._add(texture, mip, GL_STENCIL_ATTACHMENT)
        return self

    def _add(self, texture, mip, attachment_id):
        self._built = False
        if attachment_id in self._used_attachment_ids:
            raise RuntimeError("Value: {0} already in use!".format(attachment_id))
        glNamedFramebufferTexture(self.value, attachment_id, texture, mip)
        self._used_attachment_ids.append(attachment_id)

    def _create(self):
        if self._intitialized:
            return
        glCreateFramebuffers(1, self._framebuffer_ptr)
        self.value = self._framebuffer_ptr.value

    def _destroy(self):
        if self._intitialized:
            glDeleteFramebuffers(1, self._framebuffer_ptr)
            self._intitialized = False
        self.value = None
        self._built = False
        self._next_colour_id = GL_COLOR_ATTACHMENT0
        self._used_attachment_ids = []

    @contextmanager
    def bind(self):
        """Bind the framebuffer to be drawn too."""
        if not self._built:
            # Always check that our framebuffer is ok
            if(glCheckNamedFramebufferStatus(self.value, GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE):
                print("Framebuffer fail")
                exit(-1)
            self._built = True
        glBindFramebuffer(GL_FRAMEBUFFER, self.value)
        glDrawBuffers(len(self._used_attachment_ids), self._used_attachment_ids)
        yield
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glDrawBuffer(GL_BACK)
