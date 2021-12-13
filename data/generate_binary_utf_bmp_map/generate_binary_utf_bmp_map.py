"""Generates binary utf font data."""

import argparse
import os

import numpy
from PIL import Image, ImageDraw, ImageFont


def pack_into_compact_form(
        character_dimensions,
        page_ids,
        pages):
    """Packs text data into 'compact form'.
    
    This will pack the data into the following layout:
        uvec4 header; // .xy = character dimensions,
                      // .z  = bits per character
                      // .w  = number of u32s per plane
        uint planePageIds[64]; // u8s packed into u32s which contains
                               // the index that the planes data is stored at
        uint planeData[];

    Args:
        character_dimensions(tuple(int, int)) Width and height of characters.
        page_ids(numpy.array[u8]): Plane page ids.
        pages(list[numpy.array[u8]]): Unique plane page data.

    Returns:
        bytes: Compacted data.
    """
    # Construct the header data:
    #   width
    #   heigh
    #   bits per character
    #   u32 per page
    page_bit_alignment = pages[0].shape[0] * pages[0].shape[1]
    page_bit_alignment = ((page_bit_alignment-1) | 31) + 1
    page_u32_alignment = page_bit_alignment // 32
    header = numpy.array(
        [
            character_dimensions[0],
            character_dimensions[1],
            character_dimensions[0] * character_dimensions[1],
            page_u32_alignment
        ],
        dtype=numpy.uint32
    ).tobytes()

    # Reorder the page ids endianess, so they are they can be accessed via:
    #   uint32* p = &page_ids;
    #   uint32 plane_index = plane / 4;
    #   uint32 plane_shift = (plane % 4) * 8;
    #   uint32 page_id = (p[plane_index] >> plane_shift) & 0xff;
    #   uint32 page_offset = page_id * u32s_per_page;
    page_id_table = page_ids.view(">I").astype("<I").tobytes()

    # For each page, make them a continous stream of bits
    # aligned to a uint32
    compacted_pages = []
    for page in pages:
        compacted = page.reshape(
            page.shape[0] * page.shape[1]
        ).astype(numpy.uint32)
        for i in range(1, 32):
            compacted[i::32] <<= i
        compacted.resize(page_bit_alignment)
        compacted_pages.append(
            sum(compacted[i::32] for i in range(32)).tobytes()
        )

    # And finally combine the results!
    result = header + page_id_table
    # This could be done in the above loop, but seems more readable here
    for compacted in compacted_pages:
        result += compacted

    return result


def pack_into_preview_form(
        character_dimensions,
        page_ids,
        pages):
    """Packs text data into 'preview form'.

    This basically constructs a preview image, with the page offsets
    written at the top of the image.

    Args:
        character_dimensions(tuple(int, int)) Width and height of characters.
        page_ids(numpy.array[u8]): Plane page ids.
        pages(list[numpy.array[u8]]): Unique plane page data.

    Returns:
        PIL.Image: Preview image
    """
    # We are basically going to shuffle the characters so they
    # go along the X axis, this is due to characters being usually
    # longer than wide and scolling down a long image is annoying
    # Store the page ids at the very top
    image_width = 256 * max(1, character_dimensions[0])
    image_height = 1 + character_dimensions[1] * len(pages)

    image_buffer = numpy.full((image_height, image_width), 127, dtype=numpy.uint8)
    image_buffer[0, 0:256] = page_ids
    for i, page in enumerate(pages):
        y_out_start = i * character_dimensions[1] + 1
        y_out_end = (i+1) * character_dimensions[1] + 1
        for c in range(256):
            y_in_start = c * character_dimensions[1]
            y_in_end = (c + 1) * character_dimensions[1]
            x_out_start = c * character_dimensions[0]
            x_out_end = (c + 1) * character_dimensions[0]
            character = page[y_in_start:y_in_end, :]
            image_buffer[y_out_start:y_out_end, x_out_start:x_out_end] = character * 255
    return Image.fromarray(image_buffer, 'L')


def generate_plane_page(
        plane_prefix,
        font,
        text_dimensions,
        metrics,
        font_sizes,
        tolerance=127):
    write_buffer = Image.new(
        "L",
        (text_dimensions[0], text_dimensions[1]*256),
        (0,)
    )
    
    draw_context = ImageDraw.Draw(write_buffer)

    for plane_char_id in range(256):
        char_id = plane_prefix | plane_char_id
        
        # Force null and space to always be empty
        if char_id in (0, 32):
            continue

        # Align the character to be in the center and on the baseline.
        write_x = text_dimensions[0] - (font_sizes[char_id][0] // 2)
        write_y = plane_char_id * text_dimensions[1] + metrics[0]
        draw_context.text(
            (write_x, write_y),
            chr(char_id),
            font=font,
            anchor="ms",
            fill=(255,)
        )

    return (numpy.asarray(write_buffer) > tolerance).astype(numpy.uint8)


def generate_page_data(font, tolerance=127, clip_padding=False):
    """Generates page data.

    Args:
        font (PIL.ImageFont): Font to rasterize.
        tolerance (int): Tolerance for determining if an anti-aliased
            pixel should be considered visible. (Default: 127)
        clip_padding (bool): Clip empty space that's shared by all characters.
            (Default: False)

    Returns:
        tuple(tuple(int, int), numpy.array[uint8], list[numpy.array]):
            Character dimensions, page lookup, unique plane pages
    """
    metrics = font.getmetrics()
    font_sizes = [
        font.getsize(chr(c))
        for c in range(0x10000)
    ]
    text_width = max(size[0] for size in font_sizes)
    text_height = max(size[1] for size in font_sizes)

    plane_pages = (
        generate_plane_page(
            (plane << 8),
            font,
            (text_width, text_height),
            metrics,
            font_sizes,
            tolerance=tolerance
        )
        for plane in range(256)
    )

    # Gather unique pages, preserving their order
    # (allows page=0 to always be ascii)
    page_ids = numpy.zeros(256, dtype=numpy.uint8)
    pages = []
    seen_pages = {}

    for plane_id, plane_page in enumerate(plane_pages):
        hashable = plane_page.tobytes()
        if hashable not in seen_pages:
            seen_pages[hashable] = len(pages)
            pages.append(plane_page)
        page_ids[plane_id] = seen_pages[hashable]

    if clip_padding:
        clip_left = 0
        clip_right = text_width
        clip_bottom = 0
        clip_top = text_height
        while all((page[:,clip_left] == 0).all() for page in pages):
            clip_left += 1

        while all((page[:,clip_right-1] == 0).all() for page in pages):
            clip_right -= 1

        while all((page[clip_bottom::text_height, :] == 0).all() for page in pages):
            clip_bottom += 1

        while all((page[(clip_top-1)::text_height, :] == 0).all() for page in pages):
            clip_top -= 1

        if((clip_left, clip_bottom, clip_right, clip_top) != (0, 0, text_width, text_height)):
            pass

        # Not handling when we have just empty characters
        # so assuming clip_right > clip_left and clip_top > clip_bottom
        if (clip_left, clip_bottom, clip_right, clip_top) != (0, 0, text_width, text_height):
            new_text_width = clip_right - clip_left
            new_text_height = clip_top - clip_bottom

            for page_id in range(len(pages)):
                old_page = pages[page_id]
                compacted_page = numpy.zeros(
                    (new_text_height * 256, new_text_width),
                    dtype=numpy.uint8
                )
                for char_id in range(256):
                    src_x = clip_left
                    src_y = text_height * char_id + clip_top
                    dst_x = 0
                    dst_y = new_text_height * char_id
                    compacted_page[
                        dst_y:(dst_y+new_text_height),
                        dst_x:(dst_x+new_text_width)
                    ] = old_page [
                        src_y:(src_y+new_text_height),
                        src_x:(src_x+new_text_width)
                    ]
                pages[page_id] = compacted_page

            text_width = new_text_width
            text_height = new_text_height

    return (
        (text_width, text_height),
        page_ids,
        pages
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-font",
        "-i",
        help="Font file to rasterize.",
        required=True
    )
    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=16,
        help="Font size to use.",
    )
    parser.add_argument(
        "--brute-size",
        "-b",
        action="store_true",
        help="Attempt to brute force a size.",
    )
    parser.add_argument(
        "--clip-padding",
        "-c",
        action="store_true",
        help="Clip padding pixels",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="",
        help="Where to write the data in a compacted form."
    )
    parser.add_argument(
        "--preview",
        "-p",
        default="",
        help="Where to write a preview image of the data."
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
    
    args = parser.parse_args()

    if args.brute_size:
        font = None
        try:
            font = ImageFont.truetype(args.input_font, args.size)
        # If the input font-size is a no-go try every value up to 256
        # (stupid I know)
        except OSError:
            for font_size in range(1, 256):
                try:
                    font = ImageFont.truetype(args.input_font, font_size)
                    break
                except OSError:
                    pass

        if font is None:
            raise OSError("Font-size could not be determined!")

    else:
        font = ImageFont.truetype(args.input_font, args.size)
    
    page_data = generate_page_data(
        font,
        tolerance=args.tolerance,
        clip_padding=args.clip_padding
    )

    if args.preview:
        parent_dir = os.path.dirname(os.path.abspath(args.preview))
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        prev_image = pack_into_preview_form(*page_data)
        prev_image.save(args.preview)

    if args.output:
        parent_dir = os.path.dirname(os.path.abspath(args.output))
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        compact_data = pack_into_compact_form(*page_data)
        with open(args.output, "wb") as out_fp:
            out_fp.write(compact_data)
