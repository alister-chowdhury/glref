import distutils.spawn
import subprocess
import re
import os
import tempfile


from .program import generate_shader_program


_GLSLC_EXEC = distutils.spawn.find_executable("glslc")
_SPIRV_CROSS_EXEC = distutils.spawn.find_executable("spirv-cross")


class _PermutationProgram(object):

    def __init__(self, debugging, **shader_type_filepaths):
        self._shader_type_filepaths = shader_type_filepaths
        self._compile = (
            load_shader_source
            if debugging
            else optimize_shader_roundtrip
        ) 
        self._permutations = {}
        self._one = None

    def one(self):
        if self._one is None:
            kwargs = {
                shader_type: self._compile(filepath)
                for shader_type, filepath in self._shader_type_filepaths.items()
            }
            self._one = generate_shader_program(
                **kwargs
            )
        return self._one

    def get(self, **permutations):
        key = tuple(sorted(permutations.items()))
        if key not in self._permutations:
            kwargs = {
                shader_type: self._compile(filepath, permutations)
                for shader_type, filepath in self._shader_type_filepaths.items()
            }
            self._permutations[key] = generate_shader_program(
                **kwargs
            )
        return self._permutations[key]


def optimize_shader_roundtrip(filepath, macros=None):
    """Similar to load_shader_source, except it uses glslc to optimize the input GLSL
    and then uses spriv-cross to spit out a optimized version.
    """
    if not _GLSLC_EXEC:
        raise RuntimeError(
            "In order to use macros and includes glslc "
            "is needed (install the VulkanSDK)."
        )

    if not _SPIRV_CROSS_EXEC:
        raise RuntimeError(
            "In order to use macros and includes glslc "
            "is needed (install the VulkanSDK)."
        )

    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.close()
        command = [
            _GLSLC_EXEC,
            "--target-env=opengl4.5",
            "-O",
            filepath,
            "-o", tmp.name
        ]
        if macros:
            for key, value in macros.items():
                command.append("-D{0}={1}".format(key, value))
        subprocess.check_call(command)

        command = [_SPIRV_CROSS_EXEC, tmp.name]
        result = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            close_fds=True
        ).stdout.read().decode("latin-1")

        # Unwanted addon
        result = result.replace("#extension GL_GOOGLE_include_directive : enable", "")

        # Fixup up line complaints :(
        result = re.sub("#line (\d+) .+$", lambda x: "#line {0}".format(x.group(1)), result, flags=re.MULTILINE)

        return result

    finally:
        os.unlink(tmp.name)


def load_shader_source(filepath, macros=None):
    # Avoid recquiring glslc if possible
    if not macros:
        with open(filepath, "r") as in_fp:
            data = in_fp.read()
            if "#include" not in data:
                return data

    if not _GLSLC_EXEC:
        raise RuntimeError(
            "In order to use macros and includes glslc "
            "is needed (install the VulkanSDK)."
        )
    command = [
        _GLSLC_EXEC,
        "--target-env=opengl4.5",
        "-E",
        filepath,
        "-o", "-"
    ]
    if macros:
        for key, value in macros.items():
            command.append("-D{0}={1}".format(key, value))

    result = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        close_fds=True
    ).stdout.read().decode("latin-1")

    # Unwanted addon
    result = result.replace("#extension GL_GOOGLE_include_directive : enable", "")

    # Fixup up line complaints :(
    result = re.sub("#line (\d+) .+$", lambda x: "#line {0}".format(x.group(1)), result, flags=re.MULTILINE)

    return result


def make_permutation_program(debugging, **shader_type_filepaths):
    return _PermutationProgram(debugging, **shader_type_filepaths)
