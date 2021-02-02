import numpy

# Householder transformation
def make_reflection_matrix(p0, p1, p2):
    N = numpy.cross(p1-p0, p2-p0)
    N /= numpy.linalg.norm(N)
    d = -N.dot(p0)
    return numpy.matrix((
        (1-2*N[0]*N[0], -2*N[0]*N[1],  -2*N[0]*N[2],  -2*N[0]*d),
        (-2*N[1]*N[0],  1-2*N[1]*N[1], -2*N[1]*N[2],  -2*N[1]*d),
        (-2*N[2]*N[0],  -2*N[2]*N[1],  1-2*N[2]*N[2], -2*N[2]*d),
        (0, 0, 0, 1)
    ), dtype=numpy.float32)
