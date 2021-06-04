"""Generate stencil textures with an internal 2x4 subpixel layout.""" 

import argparse

import numpy
from PIL import Image, ImageDraw, ImageFont


def get_character_mapping(
        font,
        tolerance=127,
        block_offset=0):
    """Generates a character mapping for a given font.

    Args:
        font (PIL.ImageFont): Font to rasterize.
        tolerance (int): Tolerance for determining if an anti-aliased
            pixel should be considered visible. (Default: 127)
        block_offset (int): Unicode block offset,
            this determins the unicode page to use. (Default: 0)
    Returns:
        numpy.array: 2d pixel array.
    """
    metrics = font.getmetrics()
    font_sizes = [
        font.getsize(chr(c + block_offset * 256))
        for c in range(256)
    ]
    max_width = max(size[0] for size in font_sizes)
    max_height = max(size[1] for size in font_sizes)
    # It's worth noting that the width needs to be aligned to 2
    # and the height needs to be aligned 4, however because we subdivide
    # things into a grid of 16x16, this implicitly happens
    packed_image = Image.new("L", (max_width*16, max_height*16), (0,))
    draw_context = ImageDraw.Draw(packed_image)
    for c in range(256):
        x_dst_offset = (c & 0xf) * max_width
        y_dst_offset = (c >> 4) * max_height
        # Ensure nulls and spaces are empty
        if not block_offset and c in (0, 32):
            continue
        # Align the character to be in the center and on the baseline.
        x_dst_offset += max_width - (font_sizes[c][0] // 2)
        y_dst_offset += metrics[0] 
        draw_context.text(
            (x_dst_offset, y_dst_offset),
            chr(c + block_offset * 256),
            font=font,
            anchor="ms",
            fill=(255,)
        )
    packed_image = (numpy.asarray(packed_image) > tolerance).astype(
        numpy.uint8
    )
    # # Debug view texture
    # return packed_image * 255
    rows0 = packed_image[0::4, :]
    rows1 = packed_image[1::4, :] << 1
    rows2 = packed_image[2::4, :] << 2
    rows3 = packed_image[3::4, :] << 3
    rows = rows0 | rows1 | rows2 | rows3
    cols0 = rows[:, 0::2]
    cols1 = rows[:, 1::2] << 4
    return cols0 | cols1


def make_text_texture(
        ttf_path,
        size,
        output_file,
        tolerance=127,
        block_offset=0):
    """Make a texture file that contains a character mapping.

    Args:
        ttf_path (str): Path to a ttf file.
        size (int): Font size to use.
        output_file (str): Where to write the texture to.
        tolerance (int): Tolerance for determining if an anti-aliased
            pixel should be considered visible. (Default: 127)
        block_offset (int): Unicode block offset,
            this determins the unicode page to use. (Default: 0)
    """
    font = ImageFont.truetype(ttf_path, size)
    pixels = get_character_mapping(
        font,
        tolerance=tolerance,
        block_offset=block_offset
    )
    image = Image.fromarray(pixels, 'L')
    image.save(output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-ttf",
        "-i",
        help="TTF file to rasterize.",
        required=True
    )
    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=32,
        help="Font size to use.",
    )
    parser.add_argument(
        "--output-texture",
        "-o",
        help="Where to write the resulting texture.",
        required=True
    )
    parser.add_argument(
        "--tolerance",
        "-t",
        type=int,
        default=127,
        help=(
            "Tolerance for determining if an anti-aliased "
            "pixel should be considered visible"
        )
    )
    parser.add_argument(
        "--block-offset",
        "-b",
        type=int,
        default=0,
        help=(
            " Unicode block offset, "
            "this determins the unicode page to use."
        )
    )
    
    args = parser.parse_args()

    make_text_texture(
        ttf_path=args.input_ttf,
        size=args.size,
        output_file=args.output_texture,
        tolerance=args.tolerance,
        block_offset=args.block_offset
    )
