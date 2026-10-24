import sys
T = '/root/work/lanes/purge-props24/port/dreamcast/tools'
sys.path[:0] = [T, T + '/../../../tools']
import ps2_objects as po, room_smd as rs
from assetpipe.rooms import GcIso
g = GcIso(po.GC_ISO); rooms = dict(g.rooms())
for r in sys.argv[2:]:
    d = g.read(rooms[r])
    if d[:32] == rs.CONTAINER_MAGIC: d = rs.decode_das(d)
    open('%s/%s.arc' % (sys.argv[1], r), 'wb').write(d); print(r, len(d))
