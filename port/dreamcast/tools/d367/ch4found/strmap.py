import sys, struct
sys.path.insert(0, '/root/probe/lanes-20261016/ch4found/tree/port/dreamcast/tools')
import aica_banks as a
M = '/root/probe/lanes-20261014/ch22/snd/mirror-c23'
H = a.stream_headers(M)
byoff = {}
for k, v in H.items(): byoff.setdefault(v['offset'], []).append(k)
for s, r in (('36f8000', 'r218'), ('5690000', 'r227'), ('5890000', 'r222'), ('8f80000', 'r22b'), ('a0e8000', 'r229')):
    print(r, s, byoff.get(int(s, 16)))
d = open(M + '/bgm/bgmtbl.dat', 'rb').read()
room_ofs, list_ofs = struct.unpack_from('<2I', d, 0)
ids = []
while True:
    v = struct.unpack_from('<H', d, list_ofs + 2 * len(ids))[0]
    if v == 0xFFFF: break
    ids.append(v)
offs = struct.unpack_from('<%dI' % len(ids), d, room_ofs)
CH4 = [0x210,0x211,0x212,0x213,0x214,0x215,0x216,0x217,0x218,0x219,0x21a,0x21b,0x21d,0x220,0x221,0x222,0x223,0x224,0x225,0x226,0x227,0x228,0x229,0x22a,0x22b]
allst = set(); bgm0 = {}
for rid, o in zip(ids, offs):
    if rid not in CH4: continue
    r = room_ofs + o; num = struct.unpack_from('<I', d, r)[0]
    for k in range(num):
        e = struct.unpack_from('<13I', d, r + 4 + 52 * k)
        for x in e[7:13]:
            if x: allst.add((0, x & 0xFF))
        if k == 0 and e[1]: bgm0['r%03x' % rid] = e[1] & 0xFF
print('bgm0', bgm0)
CH3 = set(a.CH3_STREAMS)
print('room streams', sorted(allst), 'new vs CH3', sorted(allst - CH3))
