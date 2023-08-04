import os
import numpy
from PIL import Image


# This is all very messy and confusing, the switching between [x, y] and [y, x] only
# makes it worse.

_TEXTURES_DIR = os.path.abspath(os.path.join(__file__, "..", "textures"))
_ATLAS_BASE = os.path.abspath(os.path.join(__file__, "..", "ATLAS_BASE.png"))
_ATLAS_NORM = os.path.abspath(os.path.join(__file__, "..", "ATLAS_NORM.png"))


_FORCE_POWER_OF_TWO = False
_BLOCK_SIZE = 4

def _gather_texture_mapping():
    """Gather a mapping of textures to their respective layers.

    Returns:
        dict: Mapping
    """
    textures_files = (
        tex
        for tex in os.listdir(_TEXTURES_DIR)
        if tex.endswith(".png") and not tex.startswith(".")
    )

    mapping = {}
    for texture_file in textures_files:
        basename = os.path.basename(texture_file).rsplit(".", 1)[0]
        full_path = os.path.join(_TEXTURES_DIR, texture_file)
        image = Image.open(full_path)
        size = tuple(image.size)
        if any(((s & (_BLOCK_SIZE - 1)) != 0) for s in size):
            raise ValueError(
                "Mismatching alignment for '{0}', should be 4, got {1}".format(
                    texture_file, size
                )
            )
        name, layer = basename.rsplit("_", 1)
        if name not in mapping:
            mapping[name] = {
                "name": name,
                "layers": {layer: image},
                "size": size,
            }
        else:
            mapping[name]["layers"][layer] = image
            if mapping[name]["size"] != size:
                raise ValueError(
                    "Mismatching size for '{0}', expected {1}, got {2}".format(
                        texture_file, mapping[name]["size"], size
                    )
                )
    return mapping


def _calculate_roi(mappings):
    """Calculate the ROI, block size and numpixels based upon the base alpha.

    Args:
        mappings (dict): Mapping
    """
    for mapping in mappings.values():
        base = mapping["layers"].get("BASE")
        if base and base.mode == "RGBA":
            # Isolate to alpha regions, align to _BLOCK_SIZE for block compression
            alpha = numpy.array(base.getdata(3)).reshape(base.size)
            y_blocks = [alpha[i:i+_BLOCK_SIZE].any() for i in range(0, base.size[0], _BLOCK_SIZE)]
            x_blocks = [alpha[:,i:i+_BLOCK_SIZE].any() for i in range(0, base.size[1], _BLOCK_SIZE)]
            x0 = next((i for i, b in enumerate(x_blocks) if b), 0)
            x1 = len(x_blocks) - next((i for i, b in enumerate(reversed(x_blocks)) if b), 0)
            y0 = next((i for i, b in enumerate(y_blocks) if b), 0)
            y1 = len(y_blocks) - next((i for i, b in enumerate(reversed(y_blocks)) if b), 0)

            mapping["roi"] = (
                y0 * _BLOCK_SIZE,
                x0 * _BLOCK_SIZE,
                y1 * _BLOCK_SIZE,
                x1 * _BLOCK_SIZE
            )
            mapping["block_size"] = (y1 - y0, x1 - x0)
            mapping["numpixels"] = (y1 - y0) * (x1 - x0) * _BLOCK_SIZE * _BLOCK_SIZE
        # Default to full size if there is no base pass
        else:
            mapping["roi"] = (
                0, 0, mapping["size"][1], mapping["size"][0]
            )
            mapping["block_size"] = (mapping["size"][0]//_BLOCK_SIZE, mapping["size"][1]//_BLOCK_SIZE)
            mapping["numpixels"] = mapping["size"][0] * mapping["size"][1]

        mapping["local_uv_region"] = (
            mapping["roi"][1] / mapping["size"][1],
            mapping["roi"][3] / mapping["size"][1],
            mapping["roi"][0] / mapping["size"][0],
            mapping["roi"][2] / mapping["size"][0]
        )


def _calculate_placement(mappings):
    """Calculate the placement of tiles within the atlas.
    
    Args:
        mappings (dict): Mapping.

    Returns:
        tuple: Final texture dimensions (wxh)
    """
    mapping_values = sorted(
        mappings.values(),
        key=lambda x: (x["numpixels"], x["name"]),
        reverse=True
    )

    blocks = None

    for mapping in mapping_values:
        num_y = mapping["block_size"][0]
        num_x = mapping["block_size"][1]

        if blocks is None:
            blocks = numpy.zeros((num_y, num_x), dtype=bool)
            mapping["coord"] = (0, 0)
            continue

        end_x = blocks.shape[1]
        end_y = blocks.shape[0]

        # find first free space, not espeically efficient
        if end_y > num_y and end_x > num_x:
            y_search_end = blocks.shape[0] - num_y + 1
            x_search_end = blocks.shape[1] - num_x + 1
            found = False
            for y in range(y_search_end):
                for x in numpy.where(blocks[y, 0:x_search_end])[0]:
                    if numpy.all(blocks[y:(y+num_y),x:(x+num_x)]):
                        blocks[y:(y+num_y),x:(x+num_x)] = False
                        mapping["coord"] = (y * _BLOCK_SIZE, x * _BLOCK_SIZE)
                        found = True
                        break
                if found:
                    break
            if found:
                continue

        # Need to reallocate:
        #   * Add the bottom if it's wider then tall
        #   * Add to right if it's taller than wide
        #   * If it's square, put it on whatever axis
        #     is smaller.
        expand_dir = end_x > end_y
        if num_x > num_y:
            expand_dir = True
        elif num_y > num_x:
            expand_dir = False

        if expand_dir:
            mapping["coord"] = (end_y * _BLOCK_SIZE, 0)
            new_shape = (
                end_y + num_y,
                max(end_x, num_x)
            )
            allocate_roi = (
                end_y,
                0,
                end_y + num_y,
                num_x
            )
        else:
            mapping["coord"] = (0, end_x * _BLOCK_SIZE)
            new_shape = (
                max(end_y, num_y),
                end_x + num_x,
            )
            allocate_roi = (
                0,
                end_x,
                num_y,
                end_x + num_x,
            )

        if _FORCE_POWER_OF_TWO:
            def round_to_power2(x):
                if (x & (x-1)) != 0:
                    x |= (x >> 1)
                    x |= (x >> 2)
                    x |= (x >> 4)
                    x |= (x >> 8)
                    x |= (x >> 16)
                    x |= (x >> 32)
                    x += 1
                return x

            new_shape = (
                round_to_power2(new_shape[0]),
                round_to_power2(new_shape[1])
            )

        new_blocks = numpy.ones(new_shape, dtype=bool)
        new_blocks[0:end_y, 0:end_x] = blocks
        new_blocks[
            allocate_roi[0]:allocate_roi[2],
            allocate_roi[1]:allocate_roi[3]
        ] = False
        blocks = new_blocks


    texture_size = (blocks.shape[0] * _BLOCK_SIZE, blocks.shape[1] * _BLOCK_SIZE)

    for mapping in mapping_values:
        roi = mapping["roi"]
        coord = mapping["coord"]
        pixel_region = (
            coord[1], coord[0],
            coord[1] + (roi[3] - roi[1]),
            coord[0] + (roi[2] - roi[0])
        )
        uv_region = (
            pixel_region[0] / texture_size[0],
            pixel_region[1] / texture_size[1],
            pixel_region[2] / texture_size[0],
            pixel_region[3] / texture_size[1]
        )
        local_uv_region = (
            roi[1] / mapping["size"][1],
            roi[3] / mapping["size"][1],
            roi[0] / mapping["size"][0],
            roi[2] / mapping["size"][0]
        )
        mapping["atlas_pixel_region"] = pixel_region
        mapping["atlas_uv_region"] = uv_region

    return (blocks.shape[1] * _BLOCK_SIZE, blocks.shape[0] * _BLOCK_SIZE)


def generate_atlas(width, height, mappings, layer_name):
    data = numpy.zeros((height, width, 4), dtype=numpy.uint8)
    for mapping in mappings.values():
        layer = mapping["layers"].get(layer_name)
        if not layer:
            continue
        pixel_data = numpy.array(layer)
        if len(pixel_data.shape) > 2:
            num_channels = pixel_data.shape[2]
        else:
            num_channels = 1
        pixel_data.reshape(
            pixel_data.shape[0],
            pixel_data.shape[1],
            num_channels
        )
        roi = mapping["roi"]
        pixel_data = pixel_data[
            roi[0]:roi[2],
            roi[1]:roi[3]
        ]
        pixel_region = mapping["atlas_pixel_region"]
        data[
            pixel_region[1]:pixel_region[3],
            pixel_region[0]:pixel_region[2],
            0:num_channels
        ] = pixel_data

        # Force alpha of 1
        if num_channels < 4:
            data[
                pixel_region[1]:pixel_region[3],
                pixel_region[0]:pixel_region[2],
                3
            ] = 255
    return Image.fromarray(data)







mapping = _gather_texture_mapping()
_calculate_roi(mapping)
texture_size = _calculate_placement(mapping)
print(texture_size)
# print(mapping["WALL_L03_V0_S0"])
base = generate_atlas(texture_size[0], texture_size[1], mapping, "BASE")
base.save(_ATLAS_BASE)
norm = generate_atlas(texture_size[0], texture_size[1], mapping, "NORM")
norm.save(_ATLAS_NORM)
# print(texture_size)
# print(len(mapping))
# print(mapping)
# print({x for x in sorted(v["coord"] for k, v in mapping.items())})
