import argparse
import sys

# Lazy
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.arrays import (
    GLbyteArray,
)


SHADER_TYPES = {
    "compute": GL_COMPUTE_SHADER,
    "fragment": GL_FRAGMENT_SHADER,
    "vertex": GL_VERTEX_SHADER,

    "comp": GL_COMPUTE_SHADER,
    "frag": GL_FRAGMENT_SHADER,
    "vert": GL_VERTEX_SHADER,

    "c": GL_COMPUTE_SHADER,
    "f": GL_FRAGMENT_SHADER,
    "v": GL_VERTEX_SHADER,
}


def init_gl():
    """Initialize GL via GLUT"""
    glutInitContextVersion(4, 6)
    glutInitContextProfile(GLUT_CORE_PROFILE)
    glutInitContextFlags(GLUT_FORWARD_COMPATIBLE)
    glutInit()
    glutInitDisplayMode(GLUT_RGBA|GLUT_DEPTH|GLUT_STENCIL|GLUT_DOUBLE)
    glutInitWindowSize(1, 1)
    glutCreateWindow(b"")


def get_program_binary(program):
    """Get the binary data from a program.
        
    Args:
        program (int): GL Program.
    """
    prog_size = glGetProgramiv(program, GL_PROGRAM_BINARY_LENGTH)
    bin_format = GLenum()
    bin_data = GLbyteArray.asArray([0]*prog_size)
    glGetProgramBinary(
        program,
        prog_size,
        0,
        bin_format,
        bin_data
    )
    if (sys.version_info > (3, 0)):
        # str_data = bytes(bin_data).decode('latin-1')
        str_data = bytes(bin_data)
    else:
        str_data = "".join(
            map(lambda x: chr(x if x >= 0 else x+256), bin_data)
        )
    return str_data


def create_program(shader_file_path, shader_type=None):
    """Create a GL program.

    Args:
        shader_file_path (str): path to shader file.
        shader_type (str): shader type (Default: None)

    Returns:
        int: program
    """
    if not shader_type:
        detected_shader_type = shader_file_path.rsplit(
            ".", 1
        )[-1].lower()
        if detected_shader_type not in SHADER_TYPES:
            raise RuntimeError("Couldn't detect shader type")
        shader_type = detected_shader_type
    else:
        if shader_type.lower() not in SHADER_TYPES:
            raise RuntimeError(
                "Unknown shader type: '{0}'\n"
                .format(shader_type)
            )

    with open(shader_file_path, "r") as in_fp:
        shader_source = in_fp.read()

    shader_type = SHADER_TYPES[shader_type.lower()]
    shader = glCreateShader(shader_type)
    glShaderSource(shader, shader_source, 0)
    glCompileShader(shader);
    ok = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not ok:
        error_log = glGetShaderInfoLog(shader)
        raise RuntimeError(
            "Failed to load shader:\n{0}".format(
                error_log
            )
        )
    program = glCreateProgram()
    # glProgramParameteri(program, GL_PROGRAM_SEPARABLE, GL_TRUE)
    # glProgramParameteri(program, GL_PROGRAM_BINARY_RETRIEVABLE_HINT, GL_TRUE)
    glAttachShader(program, shader)
    glLinkProgram(program)
    ok = glGetProgramiv(program, GL_LINK_STATUS)
    if not ok:
        error_log = glGetProgramInfoLog(program)
        raise RuntimeError(
            "Failed to link shader:\n{0}".format(
                error_log
            )
        )
    glDetachShader(program, shader)
    glDeleteShader(shader)
    return program


def main(shader_file_path, shader_type=None, output=None):
    init_gl()
    program = create_program(shader_file_path, shader_type)
    data = get_program_binary(program)
    if not None:
        with open(output, "wb") as out_fp:
            out_fp.write(data)
    else:
        print(data)
    # with open("test.d", "wb") as out_fp:
    #     out_fp.write(data)


# On old nvidia, the disasm was in plaintext
# On nvidia (currently), after the first 3 bytes
# the result can be zlib.decompress'd
# but how to use that further is unclear

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Target shader file.",
        required=True
    )
    parser.add_argument(
        "-t",
        "--type",
        default=None,
        choices=list(SHADER_TYPES)
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output blob.",
        required=False
    )

    args = parser.parse_args()
    main(args.input, args.type, args.output)
