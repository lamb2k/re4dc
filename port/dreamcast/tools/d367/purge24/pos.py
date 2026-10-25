import struct, sys
T = '/root/work/lanes/purge-props24/port/dreamcast/tools'
sys.path[:0] = [T, T + '/../../../tools']
import room_smd as rs
for room in sys.argv[1:]:
    gd = open('/root/work/lanes/purge-props24-scratch/gcarc/%s.arc' % room, 'rb').read()
    for tag, s, e in rs.tagged_entries(gd, '>'):
        if tag.rstrip(b'\0') != b'ETS': continue
        n = struct.unpack_from('>H', gd, s)[0]
        for k in range(n):
            p = s + 16 + k * 40
            i, sl = struct.unpack_from('>2H', gd, p); f = struct.unpack_from('>6f', gd, p + 16)
            print(room, 'et%02x00' % i, sl, ['%.0f' % x for x in f])
