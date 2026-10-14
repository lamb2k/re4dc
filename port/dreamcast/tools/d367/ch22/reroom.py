#!/usr/bin/env python3
"""reroom.py <registry.re4nmr> <hex room> <out>: the same room-agnostic registry package for another room.
Header (tools/d367/model_registry.py write_package): 8-byte magic + 14 u32; room at byte 32, header CRC32 at 44 over the
64-byte header with that field zero. Payload (and its CRC/FNV at 36/40) is unchanged."""
import struct, sys, zlib
src, room, out = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]
d = bytearray(open(src, 'rb').read())
head = bytearray(d[:64])
old_room, old_crc = struct.unpack_from('<I', head, 32)[0], struct.unpack_from('<I', head, 44)[0]
chk = bytearray(head); struct.pack_into('<I', chk, 44, 0)
assert zlib.crc32(bytes(chk)) & 0xffffffff == old_crc, 'header CRC layout mismatch'
struct.pack_into('<I', head, 32, room); struct.pack_into('<I', head, 44, 0)
struct.pack_into('<I', head, 44, zlib.crc32(bytes(head)) & 0xffffffff)
d[:64] = head
open(out, 'wb').write(bytes(d))
print('reroom %s room %04x -> %04x %s' % (src, old_room, room, out))
