import numpy
from PIL import Image

TILE_SIZE = 64
PADDED_TILE_SIZE = TILE_SIZE + 2
PilImage = Image



def _image_to_nprgb8(image):
    """Convert a PIL image to a RGBA8 numpy array."""
    image_data = numpy.array(image.getdata(), dtype=numpy.uint8)
    if image_data.shape[1] != 4:
        if image_data.shape[1] < 4:
            # Padd RGB with black
            if image_data.shape[1] < 3:
                image_data = numpy.lib.pad(image_data, ((0, 0), (0, 3-image_data.shape[1])))
            # Padd alpha with white
            image_data = numpy.lib.pad(image_data, ((0, 0), (0, 1)), constant_values=(0xff,))
        else:
            image_data = numpy.resize(image_data, (image_data.shape[0], 4))
    image_data = numpy.reshape(image_data, (image.height, image.width, 4))
    return image_data


def _mip_chain(image):
    """Creates the next mip in a chain."""
    width = image.width >> 1
    height = image.height >> 1
    if width == 0 and height == 0:
        return None
    if width == 0:
        width = 1
    if height == 0:
        height = 1
    return image.resize((width, height), PilImage.BOX)


class Image(object):
    
    def __init__(self, filepath=r"C:\Users\thoth\Desktop\im0.png", automip=True):
        try:
            image = PilImage.open(filepath)
        
        except FileNotFoundError:
            self.valid = False
            self.mip_data = []
            self.mips = 0
            self.size = (0, 0)
            self.has_mip_tail = False

        self.mips = 1
        self.mip_data = [_image_to_nprgb8(image)]
        self.size = (image.width, image.height)
        self.has_mip_tail = False

        if automip:
            image = _mip_chain(image)
            while image is not None:
                self.mip_data.append(_image_to_nprgb8(image))
                self.mips += 1
                image = _mip_chain(image)
            self.has_mip_tail = True

    def _read_pixels(self, mip, x_start, x_end, y_start, y_end):
        buf = numpy.zeros((y_end - y_start, x_end - x_start, 4), dtype=numpy.uint8)
        if mip < self.mips:
            pixels = self.mip_data[mip]
            xdst = max(0, -x_start)
            ydst = max(0, -y_start)
            xsrc = max(0, x_start)
            ysrc = max(0, y_start)
            width = min(x_end, pixels.shape[1]) - x_start - xdst
            height = min(y_end, pixels.shape[0]) - y_start - ydst
            # print(xdst, ydst)
            # print(xsrc, ysrc)
            # print(width, height)
            buf[ydst:ydst+height, xdst:xdst+width] = pixels[ysrc:ysrc+height, xsrc:xsrc+width]
        return buf

    def read_tile(self, mip, x, y):
        # Not a mip tail tile
        tile_start_x = x * TILE_SIZE - 1
        tile_end_x = tile_start_x + PADDED_TILE_SIZE
        
        tile_start_y = y * TILE_SIZE - 1
        tile_end_y = tile_start_y + PADDED_TILE_SIZE

        data = self._read_pixels(
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
