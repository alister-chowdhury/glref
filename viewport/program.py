from OpenGL.GL import *


_SHADER_NICE_NAME = {
    GL_COMPUTE_SHADER: "GL_COMPUTE_SHADER",
    GL_VERTEX_SHADER: "GL_VERTEX_SHADER",
    GL_TESS_CONTROL_SHADER: "GL_TESS_CONTROL_SHADER",
    GL_TESS_EVALUATION_SHADER: "GL_TESS_EVALUATION_SHADER",
    GL_GEOMETRY_SHADER: "GL_GEOMETRY_SHADER",
    GL_FRAGMENT_SHADER: "GL_FRAGMENT_SHADER",
}

_INVERSE_SHADER_NAME = {
    value: key
    for key, value in _SHADER_NICE_NAME.items()
}


def build_shader(source, shader_type=GL_VERTEX_SHADER):
    shader_id = glCreateShader(shader_type)
    glShaderSource(shader_id, source, 0)
    glCompileShader(shader_id)
    ok = glGetShaderiv(shader_id, GL_COMPILE_STATUS)
    if not ok:
        error_log = glGetShaderInfoLog(shader_id)
        raise RuntimeError(
            "Failed to load {0} shader:\n{1}".format(
                _SHADER_NICE_NAME[shader_type],
                error_log,
            )
        )
    return shader_id


def generate_shader_program(**shader_type_source):
    """Generate a shader_program.

    Usage:
        generate_shader_program(
            GL_VERTEX_SHADER = vertex_source,
            GL_FRAGMENT_SHADER = frag_source,
        )
    """
    shader_ids = [
        build_shader(source, _INVERSE_SHADER_NAME[shader_type_name])
        for shader_type_name, source in shader_type_source.items()
    ]

    # Attach
    main_program = glCreateProgram()
    for shader_id in shader_ids:
        glAttachShader(main_program, shader_id)
    glLinkProgram(main_program)

    ok = glGetProgramiv(main_program, GL_LINK_STATUS)
    if not ok:
        error_log = glGetProgramInfoLog(main_program)
        raise RuntimeError("Failed to link program:\n{0}".format(error_log))

    for shader_id in shader_ids:
        glDetachShader(main_program, shader_id)
        glDeleteShader(shader_id)

    return main_program