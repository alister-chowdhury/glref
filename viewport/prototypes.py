import numpy


# Cube

PUV_CUBE_VERTICES = numpy.array([
    # P                   UV
    # front
    -1.0,  -1.0,  1.0,    0.0, 0.0,
    1.0,   -1.0,  1.0,    1.0, 0.0,
    1.0,   1.0,   1.0,    1.0, 1.0,
    -1.0,  1.0,   1.0,    0.0, 1.0,
    # back
    -1.0,  -1.0, -1.0,    0.0, 0.0,
    1.0,   -1.0, -1.0,    1.0, 0.0,
    1.0,   1.0,  -1.0,    1.0, 1.0,
    -1.0,  1.0,  -1.0,    0.0, 1.0
], dtype=numpy.float32)


CUBE_INDICES = numpy.array([
    # front
    0, 1, 2,
    2, 3, 0,
    # top
    1, 5, 6,
    6, 2, 1,
    # back
    7, 6, 5,
    5, 4, 7,
    # bottom
    4, 0, 3,
    3, 7, 4,
    # left
    4, 5, 1,
    1, 0, 4,
    # right
    3, 2, 6,
    6, 7, 3,

], dtype=numpy.uint32)


# Plane

PUV_PLANE_VERTICES = numpy.array([
    # P                   UV
    -1.0, 0.0, -1.0,      0.0, 0.0,
     1.0, 0.0, -1.0,      1.0, 0.0,
     1.0, 0.0, 1.0,       1.0, 1.0,
    -1.0, 0.0, 1.0,       0.0, 1.0,
], dtype=numpy.float32)


PNUV_PLANE_VERTICES = numpy.array([
    # P                   N                   UV
    -1.0, 0.0, -1.0,      0.0, 1.0, 0.0,      0.0, 0.0,
     1.0, 0.0, -1.0,      0.0, 1.0, 0.0,      1.0, 0.0,
     1.0, 0.0, 1.0,       0.0, 1.0, 0.0,      1.0, 1.0,
    -1.0, 0.0, 1.0,       0.0, 1.0, 0.0,      0.0, 1.0,
], dtype=numpy.float32)

PLANE_INDICES = numpy.array([
    0, 1, 2,
    2, 3, 0,
], dtype=numpy.uint32)

