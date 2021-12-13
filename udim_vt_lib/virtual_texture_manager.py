import threading
from time import sleep



class Tile(object):

    def __init__(self):
        self.next = None
        self.prev = None
        self.used_id = -1
        self.offset = None
        self.last_access = -1
        self.indirection_offset = None

class SetIndTileEvent(object):
    
    def __init__(self, indirection_offset, value):
        self.indirection_offset = indirection_offset
        self.value = value

class EventNode(object):

    def __init__(self):
        self.next = None
        self.func = None


class TileAllocator(object):

    def __init__(self, dimensions):
        head, tail = self._build_tile_list(dimensions)
        self._head = head
        self._tail = tail
        self._id_to_tile = {}
        self._input_requests = set()
        self._new_requests_flag = False
        self._access_id = 0
        self._kill = False
        self._external_updates = []

    def update_requests(self, new_requests):
        self._access_id += 1
        self._input_requests = new_requests
        self._new_requests_flag = True

    def _thread_runner(self):
        local_requests = set()
        local_acc_id = self._access_id
        while not self._kill:
            if self._new_requests_flag:
                tmp_requests = self._input_requests
                local_acc_id = self.local_acc_id
                self._new_requests_flag = False

                # First of all mark all used things so we don't accidentally
                # overwrite them, only bothering with missing tiles
                local_requests.clear()
                for request in tmp_requests:
                    if next_item in self._id_to_tile:
                        tile_node = self._id_to_tile[next_item]
                        tile_node.last_access = local_acc_id
                        self._move_front(tile_node)
                    else:
                        local_requests.add(request)

            # In C++ we would use a conditional variable or something
            if not local_requests:
                sleep(0.03)
                continue

            next_item = local_requests.pop()
            tail = self._tail

            # We cannot allocate form the tail, don't process any further
            if tail.last_access == local_acc_id:
                local_requests.clear()
                continue

            udim = request & 0xffffffff
            packed = udim >> 32
            mip = packed >> 20
            tile_y = (packed >> 10) & 0x3ff
            tile_x = packed & 0x3ff

            # Invalid udim, don't care
            if udim == 0xffffffff:
                continue

            udim_x = (udim >> 16) & 0xffff
            udim_y = udim & 0xffff
            udim_info_offset = self._udim_info_offsets[udim_x, udim_y]
            ind_offset = UdimMipAddress.unpack(self._udim_info[udim_info_offset+3+mip])
            ind_offset = (ind_offset.startX + tile_x, ind_offset.startY + tile_y, ind_offset.layer)

            tile_data = self.offset_udim_to_image[udim].read_tile(mip, tile_x, tile_y)

            #######################################
            #
            #   THIS IS WHERE YOU WERE ADDING LOGIC TO FIGURE OUT THE UDIM
            #   ITS INDIRECTION ADDRESS AND WHICH IMAGE TO READ FROM AND WHERE
            #
            #####################################

            # Update the global list
            self._tail = tail.prev
            self._tail.next = None
            self._move_front(tail)

            events = []

            # Add an event to clear the tile
            if tail.used_id in self._id_to_tile:
                del self._id_to_tile[tail.used_id]
                events.append(SetIndTileEvent(tail.indirection_offset, 0xffff))

            events.append(SetIndTileEvent(ind_offset, tail.offset))




    def _move_front(self, node):
        last_head = self._head
        if node.next is None:
            self._tail = node.prev
        self._head = node
        node.prev = None
        node.next = last_head

    @staticmethod
    def _build_tile_list(dimensions):
        dummy_first = Tile()
        first = dummy_first
        last = first
        for z in dimensions[2]:
            for y in dimensions[1]:
                for x in dimensions[0]:
                    new_tile = Tile();
                    new_tile.offset = TileAddress(x=x, y=x, layer=z).pack()
                    new_tile.prev = last
                    last.next = new_tile
        first = dummy_first.next
        return (first, last)