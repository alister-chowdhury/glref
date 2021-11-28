import numpy


# Ok, so at some point OIIO and Python3 became rather incompatible on windows.
# This is at-least partially to blame on python3.8 enforcing add_dll_directory
# and windows be awful at reporting missing deps.
# Even with all that taken care of, python starts complaining in renderdoc
# "The operating system cannot run %1."
#
# So for now, unfortunatley, we cannot use OIIO and will have to resort
# to PIL

import OpenImageIO


TILE_SIZE = 64
PADDED_TILE_SIZE = TILE_SIZE + 2

IMAGE_CACHE = OpenImageIO.ImageCache(True)


def read_pixels(image_handle, mip, x_start, x_end, y_start, y_end):
    """Read a portion of the input image."""
    return IMAGE_CACHE.get_pixels(
        image_handle,
        0, mip,
        x_start, x_end,
        y_start, y_end,
        0, 1,
        OpenImageIO.UINT8
    )


class Image(object):
    
    def __init__(self, filepath=r"C:\Users\thoth\Desktop\im0.png"):
        # OIIO on python doesn't expose ImageHandle* instances
        self._image_handle = filepath

        # Gather dimensions, mip count etc, substitute for ImageCache.get_image_info
        inspect = OpenImageIO.ImageInput.open(filepath)
        self.valid = inspect.valid_file(filepath)
        if self.valid:
            spec = inspect.spec()
            self.mips = 0
            self.size = (spec.full_width, spec.full_height)
            self.nchannels = spec.nchannels
            self.format = spec.format
            while spec.nchannels:
                self.mips += 1
                spec = inspect.spec_dimensions(0, self.mips)
            self.has_mip_tail = (max(*self.size) >> (self.mips - 1)) < TILE_SIZE

        else:
            self.mips = 0
            self.size = (0, 0)
            self.nchannels = 0
            self.format = None
            self.has_mip_tail = False

    def read_tile(self, mip, x, y):
        # Not a mip tail tile
        tile_start_x = x * TILE_SIZE - 1
        tile_end_x = tile_start_x + PADDED_TILE_SIZE
        
        tile_start_y = y * TILE_SIZE - 1
        tile_end_y = tile_start_y + PADDED_TILE_SIZE

        data = read_pixels(
            self._image_handle,
            mip,
            tile_start_x, tile_end_x,
            tile_start_y, tile_end_y
        )

        # Deal with OOB data by clamping it
        if x == 0:
            data[:,0] = data[:,1]

        if y == 0:
            data[0] = data[1]

        width = max(1, self.size[0] >> mip)
        height = max(1, self.size[1] >> mip)

        if width <= tile_end_x:
            data[:, (tile_end_x - width)] = data[:, (tile_end_x - width - 1)]

        if height <= tile_end_y:
            data[(tile_end_y - height)] = data[(tile_end_y - height - 1)]

        return data



# r"C:\Users\thoth\Desktop\im0.png"

# import code

# code.interact(local=locals())



"""
            w = self._framebuffer2_col._width
            h = self._framebuffer2_col._height
            arr = numpy.zeros((w, h), dtype=numpy.uint32)
            glGetTextureSubImage(
                self._framebuffer2_col.texture,
                0,
                0, 0, 0,
                w, h, 1,
                GL_RED,
                GL_UNSIGNED_INT,
                w * h * 4,
                arr
            )
"""