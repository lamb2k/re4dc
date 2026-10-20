#!/usr/bin/env python3
"""nmr_retarget.py <in registry.re4nmr> <out registry.re4nmr> <room hex>   (lane ch2rooms20, 2026-10-20)

A room-owned model registry package (model_registry.py write_package) for another room whose cast is the same
descriptors: only the header's room word (offset 32) and its header CRC (offset 44, zlib.crc32 of the 64-byte header
with that word 0) change; the payload, its CRC / FNV and every descriptor are byte-identical. Proof it is how
model_registry.py differs between rooms: the release disc's r102 and r112 merchant packages (same spec,
ps2-merchant18: rooms r102 r10d r10e r112) differ in exactly those 5 bytes.
"""
import struct
import sys
import zlib

HEADER = 64


def main():
    src, dst, room = sys.argv[1], sys.argv[2], int(sys.argv[3], 16)
    d = bytearray(open(src, 'rb').read())
    assert d[:8] == b'RE4NMR1\0', src
    head = bytearray(d[:HEADER])
    struct.pack_into('<I', head, 44, 0)
    assert zlib.crc32(bytes(head)) & 0xffffffff == struct.unpack_from('<I', d, 44)[0], 'header CRC check failed: ' + src
    struct.pack_into('<I', head, 32, room)
    struct.pack_into('<I', head, 44, zlib.crc32(bytes(head)) & 0xffffffff)
    d[:HEADER] = head
    open(dst, 'wb').write(d)
    print('nmr_retarget: %s room %03x -> %s room %03x' % (src, struct.unpack_from('<I', open(src, 'rb').read(), 32)[0], dst, room))


if __name__ == '__main__':
    main()
