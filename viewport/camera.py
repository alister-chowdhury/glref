from math import radians, tan
import numpy


__all__ = ("Camera",)


def make_perspective_matrix(aspect, fov=90.0):
    near = 0.05
    far = 1000
    top = near * tan(0.5 * radians(fov))
    bottom = -top
    right = top * aspect
    left = -right

    m00 = (2*near)/(right-left)
    m11 = (2*near)/(top-bottom)
    m20 = (right+left)/(right-left)
    m21 = (top+bottom)/(top-bottom)
    m22 = -(far+near)/(far-near)
    m32 = -(2*far*near)/(far-near)

    projection = numpy.matrix([
        [m00, 0, 0, 0],
        [0, m11, 0, 0],
        [m20, m21, m22, -1],
        [0, 0, m32, 0]
    ], dtype=numpy.float32)
    return projection


class Camera(object):

    def __init__(self):
        # View settings
        self._eye = numpy.array([0.0, 0.0, 0.0])
        self._right = numpy.array([1.0, 0.0, 0.0])
        self._up = numpy.array([0.0, 1.0, 0.0])
        self._forward = numpy.array([0.0, 0.0, 1.0])

        # Projection settings
        self._fov = 90.0
        self._aspect = 1.0

        self._view = None
        self._projection = None
        self._view_projection = None

    @property
    def eye(self):
        return self._eye

    @property
    def view(self):
        if self._view is None:
            tx = self._right.dot(self._eye)
            ty = self._up.dot(self._eye)
            tz = -self._forward.dot(self._eye)

            self._view = numpy.matrix([
                [self._right[0], self._up[0], self._forward[0], 0],
                [self._right[1], self._up[1], self._forward[1], 0],
                [self._right[2], self._up[2], self._forward[2], 0],
                [tx, ty, tz, 1]
            ], dtype=numpy.float32)

        return self._view
    
    @property
    def projection(self):
        if self._projection is None:
            self._projection = make_perspective_matrix(
                self._aspect, self._fov
            )
        return self._projection

    @property
    def view_projection(self):
        if self._view_projection is None:
            self._view_projection = self.view * self.projection
        return self._view_projection
    
    def set_fov(self, fov):
        self._fov = fov
        self._projection = None
        self._view_projection = None

    def set_aspect(self, aspect):
        self._aspect = aspect
        self._projection = None
        self._view_projection = None

    def move(self, xyz):
        self._eye = self._eye + xyz
        self._view = None
        self._view_projection = None

    def set_position(self, xyz):
        self._eye = xyz
        self._view = None
        self._view_projection = None

    def look_at(self, target, eye=None):
        if eye is not None:
            self._eye = eye
        else:
            eye = self._eye

        self._forward = eye - target
        self._forward = self._forward / numpy.linalg.norm(self._forward)

        self._right = numpy.cross(numpy.array([0, 1, 0]), self._forward)
        self._right = self._right / numpy.linalg.norm(self._right)

        self._up = numpy.cross(self._forward, self._right)
        self._up = self._up / numpy.linalg.norm(self._up)

        self._view = None
        self._view_projection = None
