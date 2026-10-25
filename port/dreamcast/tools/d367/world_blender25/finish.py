# world-blender25: make a regrouped r101 arm shippable-shaped (WSL python):
#   r4pw  rekeyed to the shipped mip22 texture keys (r4pw_rekey.py: ctl original r4pw -> shipped r4pw key map)
#   ids   regenerated for the new placements (ps2_room_ids via r4pw_rekey --obj), bound to the new R4PW crc
#   r4tc  class per new part from the shipped (key, pass, cull) -> class map, bound to the new R4PW crc
#   r4sg  header policy field rebound to the new R4PW crc (payload/CRC unchanged)
# No certificate row: a regrouped R4PW matches none, so the runtime binds companions to its actual crc.
# usage: finish.py <arm final dir> <out dir>
import struct, subprocess, sys, zlib, shutil, os
X = '/root/work/lanes/world-blender25-scratch'
T = '/root/work/lanes/world-blender25/port/dreamcast/tools'
OBJ = '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/from-main/ps2/r101_004.scenario.obj'
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
shutil.copy(src + '/ps2-world.re4mesh', out)
subprocess.run(['python3', T + '/d367/ps2world/r4pw_rekey.py', src + '/ps2-world.r4pw', X + '/r101-ctl/final/ps2-world.r4pw',
                X + '/shipped/r101/ps2-world.r4pw', out + '/ps2-world.r4pw'], check=True)
# placement fields -> ordinals (runtime: ids count == placements, ids[field]); ids from the OBJ group of the old field
sys.path.insert(0, T)
import ps2_room_ids
gid = ps2_room_ids.group_ids(OBJ)
pw = bytearray(open(out + '/ps2-world.r4pw', 'rb').read())
_, _, npl, nparts, _, _ = struct.unpack_from('<4s5I', pw)
idv = []
for i in range(npl):
    o = 32 + 16 * nparts + 52 * i
    m, f = struct.unpack_from('<HH', pw, o)
    idv.append(min(gid[f], 0xFF) if f < len(gid) else 0xFF)
    struct.pack_into('<HH', pw, o, m, i)
struct.pack_into('<I', pw, 20, zlib.crc32(bytes(pw[32:])))
pw = bytes(pw); open(out + '/ps2-world.r4pw', 'wb').write(pw)
ids = struct.pack('<4s3I', b'R4ID', 1, npl, struct.unpack_from('<I', pw, 20)[0]) + bytes(idv)
open(out + '/ps2-world.ids', 'wb').write(ids + bytes(-len(ids) % 32))
_, _, npl, nparts, nmesh, crc = struct.unpack_from('<4s5I', pw)
parts = [struct.unpack_from('<IIHHBBBB', pw, 32 + 16 * i) for i in range(nparts)]
spw = open(X + '/shipped/r101/ps2-world.r4pw', 'rb').read(); stc = open(X + '/shipped/r101/ps2-world.r4tc', 'rb').read()
sn = struct.unpack_from('<4s5I', spw)[3]
scls = stc[24:24 + sn]
cmap = {}
for i in range(sn):
    p = struct.unpack_from('<IIHHBBBB', spw, 32 + 16 * i)
    k = (p[0], p[1], p[4]); c = scls[i]
    assert cmap.get(k, c) == c, ('ambiguous class', k)
    cmap[k] = c
cls = bytes(cmap[(p[0], p[1], p[4])] for p in parts)
tc = struct.pack('<4s5I', b'R4TC', 1, struct.unpack_from('<I', stc, 8)[0], nparts, crc, zlib.crc32(cls)) + cls + bytes(-nparts % 4)
open(out + '/ps2-world.r4tc', 'wb').write(tc)
sg = bytearray(open(src + '/ps2-world.r4sg', 'rb').read())
struct.pack_into('<I', sg, 24, crc)
open(out + '/ps2-world.r4sg', 'wb').write(bytes(sg))
print('FINISH placements %d parts %d meshes %d r4pw crc %08x' % (npl, nparts, nmesh, crc))
