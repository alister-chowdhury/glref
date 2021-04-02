from OpenGL.GL import *


_EXTENSIONS = None


def get_gl_extensions():
    """Get the set of GL extensions available.

    Returns:
        frozenset[str]: GL extension names.
    """
    global _EXTENSIONS
    if _EXTENSIONS is None:
        _EXTENSIONS = frozenset((
            glGetStringi(GL_EXTENSIONS, n).decode("latin-1")
            for n in range(glGetIntegerv(GL_NUM_EXTENSIONS))
        ))
    return _EXTENSIONS


def has_gl_extension(ext_name):
    """Check if a GL extension is supported.
    e.g:
        has_gl_extension("GL_NV_mesh_shader")

    Args:
        ext_name (str): Extension name.

    Returns:
        bool: True if supported.
    """
    if not isinstance(ext_name, str):
        ext_name = ext_name.decode("latin-1")
    return ext_name in get_gl_extensions()
