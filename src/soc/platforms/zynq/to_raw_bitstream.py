import struct
from io import BytesIO


def flip32(data):
    sl = struct.Struct('<I')
    sb = struct.Struct('>I')
    d = bytearray(len(data))
    for offset in range(0, len(data), 4):
        sb.pack_into(d, offset, sl.unpack_from(data, offset)[0])
    return d


def bit2bin(bitstream, flip_data=False):
    bitfile = BytesIO(bitstream)

    short = struct.Struct('>H')
    ulong = struct.Struct('>I')

    l = short.unpack(bitfile.read(2))[0]
    if l != 9:
        raise Exception("Missing <0009> header (0x%x), not a bit file" % l)
    bitfile.read(l)
    l = short.unpack(bitfile.read(2))[0]
    d = bitfile.read(l)
    if d != b'a':
        raise Exception("Missing <a> header, not a bit file")

    l = short.unpack(bitfile.read(2))[0]
    d = bitfile.read(l)

    KEYNAMES = {b'b': "Partname", b'c': "Date", b'd': "Time"}
    while 1:
        k = bitfile.read(1)
        if not k:
            bitfile.close()
            raise Exception("unexpected EOF")
        elif k == b'e':
            l = ulong.unpack(bitfile.read(4))[0]
            d = bitfile.read(l)
            if flip_data:
                return flip32(d)
            else:
                return d
        elif k in KEYNAMES:
            l = short.unpack(bitfile.read(2))[0]
            d = bitfile.read(l)
            #print(KEYNAMES[k], d)
        else:
            print("Unexpected key: %s" % k)
            l = short.unpack(bitfile.read(2))[0]
            d = bitfile.read(l)
