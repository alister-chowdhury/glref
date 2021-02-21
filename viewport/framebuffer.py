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

