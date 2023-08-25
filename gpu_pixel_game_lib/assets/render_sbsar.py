import distutils.spawn
import subprocess
import tempfile
import os
import json

_SBSRENDER_PATH = os.getenv(
    "SBSRENDER_PATH",
    distutils.spawn.find_executable("sbsrender")
)

_SBSAR_DIR = os.path.abspath(
    os.path.join(__file__, "..", "sbsar")
)

_TEXTURES_DIR = os.path.abspath(
    os.path.join(__file__, "..", "textures")
)

if not _SBSRENDER_PATH:
    raise RuntimeError(
        "Unable to find `sbsrender`, point SBSRENDER_PATH to it."
    )


def _sbsrender_command(
        sbsar,
        texture_group_name,
        parameters=None,
        outputs=("BASE", "NORM")):
    
    command = [
        _SBSRENDER_PATH,
        "render",
        "--input={0}.sbsar".format(os.path.join(_SBSAR_DIR, sbsar)),
        "--output-name={0}_{{outputNodeName}}".format(texture_group_name),
         "--output-path={0}".format(_TEXTURES_DIR)
    ]

    parameters = parameters or ()
    if isinstance(parameters, dict):
        parameters = parameters.items()

    for key, value in parameters:
        if isinstance(value, (list, set, tuple)):
            value = ",".join(value)
        command.append("--set-value={0}@{1}".format(key, value))

    for output in outputs:
        command.append("--input-graph-output={0}".format(output))

    return command



def _generate_brick_commands():
    """Generate commands for rendering brick tiles."""
    corruption_levels = 8
    min_cracks = 20
    max_cracks = 1000
    variants = 4
    for level in range(corruption_levels):
        interp = level / (corruption_levels - 1) * 0.99
        cracks = round(min_cracks * (1 - interp) + max_cracks * interp)
        seed_base = 0x100 + level * variants + cracks
        swap = interp > 0.5
        if swap:
            interp = 0.5 - abs(interp - 0.5)
        swap = int(swap)
        for variant in range(variants):
            name = "BRICKS_L{0:02d}_V{1}".format(level, variant)
            cmd = _sbsrender_command(
                "bricks_v01",
                name,
                parameters = {
                    "BrickRandDist": interp,
                    "SwapPrimaries": swap,
                    "Cracks": cracks,
                    "$randomseed": seed_base + variant
                }
            )
            yield name, cmd


def _generate_blood_decal_commands():
    """Generate commands for rendering blood tiles."""
    variants = 4
    for variant in range(variants):
        name = "BLOOD_DECL_V{0}".format(variant)
        cmd = _sbsrender_command(
            "blood_decal_v01",
            name,
            parameters = {
                "$randomseed": variant * 10
            }
        )
        yield name, cmd


def _generate_wall_commands():
    """Generate commands for rendering wall tiles."""
    corruption_levels = 8
    variants = 4
    for level in range(corruption_levels):
        cracks = level / (corruption_levels - 1) + 0.1
        for side in range(3):
            if side == 0:
                top = True
                right = False
            elif side == 1:
                top = False
                right = True
            else:
                top = True
                right = True
            seed_base = 0x210 * side + level * variants
            for variant in range(variants):
                name = "WALL_L{0:02d}_V{1}_S{2}".format(level, variant, side)
                cmd = _sbsrender_command(
                    "wall_v01",
                    name,
                    parameters = {
                        "Top": int(top),
                        "Right": int(right),
                        "Cracks": cracks,
                        "$randomseed": seed_base + variant
                    }
                )
                yield name, cmd

def _generate_ground_commands():
    """Generate commands for rendering ground tiles."""
    corruption_levels = 8
    variants = 4
    for level in range(corruption_levels):
        corruption = level / (corruption_levels - 1)
        seed_base = 0x2112 * level * variants
        for variant in range(variants):
            name = "GROUND_L{0:02d}_V{1}".format(level, variant)
            cmd = _sbsrender_command(
                "ground_v01",
                name,
                parameters = {
                    "corruption": corruption,
                    "$randomseed": seed_base + variant
                }
            )
            yield name, cmd

def _dispatch(args):
    name, cmd = args
    subprocess.check_call(cmd, stdout=subprocess.PIPE)
    return name


if __name__ == "__main__":
    generators = (
        _generate_brick_commands,
        _generate_blood_decal_commands,

        # No longer using walls
        # _generate_wall_commands,

        _generate_ground_commands,
    )

    cmds = (
        (name, cmd)
        for generator in generators
        for name, cmd in generator()
    )

    from multiprocessing import Pool
    pool = Pool(4)
    
    for done in pool.map(_dispatch, cmds):
        print("Cooked: {0}".format(done))
