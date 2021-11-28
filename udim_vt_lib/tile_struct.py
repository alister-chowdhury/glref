import ctypes


# Udim indirection entries, these point to where the mips tiles can be
# located within a sequence-wide indirection texture, pointing to the
# final indirection TileAddress
#
#   struct UdimMipAddress
#   {
#       u32 startX:12; // [0, 4095]
#       u32 startY:12; // [0, 4095]
#       u32 layer:8;   // [0, 255]
#   };
#
class UdimMipAddress(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ("startX", ctypes.c_uint32, 12),    # [0, 4095]
        ("startY", ctypes.c_uint32, 12),    # [0, 4095]
        ("layer", ctypes.c_uint32, 8),      # [0, 255]
    )

    def pack(self):
        return _UdimMipAddressUnion(parts=self).packed

    @staticmethod
    def unpack(packed):
        return _UdimMipAddressUnion(packed=packed).parts


# Tiles are stored as 64x64 pixels with a 1px border for hardware interp
# within a 8192x8192 texture (8px waste on the right and bottom).
# Extra pixels could be possibly used for something else like 1x1 data.
#
#   struct TileAddress
#   {
#       u16     x:7;        // [0, 124] ; 125-127 = invalid
#       u16     y:7;        // [0, 124] ; 125-127 = invalid
#       u16     layer:2;    // [0, 3]
#   };
#
class TileAddress(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ("x", ctypes.c_uint16, 7),       # [0, 124] ; 125-127 = invalid
        ("y", ctypes.c_uint16, 7),       # [0, 124] ; 125-127 = invalid
        ("layer", ctypes.c_uint16, 2),   # [0, 3]
    )

    def pack(self):
        return _TileAddressUnion(parts=self).packed

    @staticmethod
    def unpack(packed):
        return _TileAddressUnion(packed=packed).parts



class _TileAddressUnion(ctypes.Union):
    _fields_ = [
        ("packed", ctypes.c_uint16),
        ("parts", TileAddress)
    ]

class _UdimMipAddressUnion(ctypes.Union):
    _fields_ = [
        ("packed", ctypes.c_uint32),
        ("parts", UdimMipAddress)
    ]
