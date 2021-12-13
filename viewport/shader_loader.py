import distutils.spawn
import subprocess
import re

_GLSLC_EXEC = distutils.spawn.find_executable("glslc")




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
