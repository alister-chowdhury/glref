import numpy

from . tile_struct import UdimMipAddress


class UdimIndirectionBuilder(object):

    def __init__(self, udim_entries):
        self._udim_entries = udim_entries
        self._init_data()
        self._allocate_mip_indirections()


    def _init_data(self):
        # First determine the bounds we're going to need for the UdimInfoStart texture
        udim_entries_iter = iter(self._udim_entries)
        entry = next(udim_entries_iter)
        min_x = entry.udim_xy[0]
        max_x = entry.udim_xy[0]
        min_y = entry.udim_xy[1]
        max_y = entry.udim_xy[1]

        for entry in udim_entries_iter:
            x = entry.udim_xy[0]
            y = entry.udim_xy[1]
            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y

        self.udim_offset = (min_x, min_y)
        self.udim_info_start = numpy.full(
            (
                (max_y-min_y + 1),
                (max_x-min_x + 1),
            ),
            0xffffffff,
            dtype=numpy.uint32
        )

        # Allocate the udim info here (even if it's populated later)
        # and write back into udim_info_start
        udim_info = []
        for entry in self._udim_entries:
            x = entry.udim_xy[0] - min_x
            y = entry.udim_xy[1] - min_y
            self.udim_info_start[y, x] = len(udim_info)

            image = entry.image
            width = image.size[0]
            height = image.size[1]
            mips = image.mips
            udim_info.extend((width, height, mips))
            udim_info.extend([0] * mips)

        # If GLSL supported uint16, this could be that
        # realistically we COULD make this a 1d texture
        self.udim_info = numpy.array(udim_info, dtype=numpy.uint32)


    def _allocate_mip_indirections(self):
        pages = [_UdimPage()]

        # Add things to the layers, starting from the biggest mips (dimension wise),
        # to the lowest.
        # Were doing this by unrolling the mips into a single sequence and sorting them
        # (there is probably a smarter way to do this)
        expanded_mips = []

        for entry in self._udim_entries:
            width = entry.image.size[0]
            height = entry.image.size[1]
            mips = entry.image.mips
            for mip in range(entry.image.mips):
                expanded_mips.append(
                    (
                        # Store the tile size, not pixel size
                        (width + 63)//64,
                        (height + 63)//64,
                        mip,
                        entry
                    )
                )
                width = max(1, width >> 1)
                height = max(1, height >> 1)

        # Sort by tile count
        expanded_mips.sort(
            key = lambda x: x[0] * x[1],
            reverse = True
        )

        for tile_w, tile_h, mip, entry in expanded_mips:
            alloc = None
            layer = 0
            for layer, page in enumerate(pages):
                alloc = page.allocate(tile_w, tile_h)
                if alloc is not None:
                    break

            # Need to add a new page
            if not alloc:
                page = _UdimPage()
                layer = len(pages)
                pages.append(page)
                alloc = page.allocate(tile_w, tile_h)

            # Write back to the info table!
            udim_start = self.udim_info_start[
                entry.udim_xy[1] - self.udim_offset[1],
                entry.udim_xy[0] - self.udim_offset[0],
            ]
            self.udim_info[udim_start + 3 + mip] = UdimMipAddress(
                startX = alloc[0],
                startY = alloc[1],
                layer = layer,
            ).pack()

        self.mip_indirection_size = (
            max(page.max_written_x for page in pages),
            max(page.max_written_y for page in pages),
            len(pages)
        )


class UdimEntry(object):
    def __init__(self, udim_xy, image):
        self.udim_xy = udim_xy
        self.image = image


class _UdimPage(object):

    def __init__(self, max_dimension=4096):
        # Start off with a 1x1
        self._page = numpy.zeros((max_dimension, max_dimension), dtype=numpy.uint8)
        # Keep track of free space for rows and cols
        self._space_x = numpy.full(max_dimension, max_dimension)
        self._space_y = numpy.full(max_dimension, max_dimension)
        self.max_written_x = 0
        self.max_written_y = 0

    def allocate(self, width, height):
        for y in range(len(self._space_x) - height):
            # It looks like we may be able to allocate here
            if (width <= self._space_x[y:y+height]).all():
                # Find a spot if possible
                for x in range(self._page.shape[1] - width):
                    # Lazy python version to check if entire grid is free
                    if (self._page[y:y+height, x:x+width] == 0).all():
                        self._page[y:y+height, x:x+width] = 1
                        self.max_written_x = max(self.max_written_x, x+width)
                        self.max_written_y = max(self.max_written_y, y+height)
                        self._space_x[y:y+height] -= width
                        self._space_y[x:x+width] -= height
                        return (x, y)
        return None
