"""Island (stage 3) disc payload, measured from the lane data on ext4 (bytes)."""
import os, glob, json, struct, collections
S = '/root/probe/lanes-20261014/st3'
rooms = collections.OrderedDict()
def sz(p): return os.path.getsize(p) if os.path.exists(p) else 0
inv = {x['room']: x for x in json.load(open('/mnt/c/Game Dev/Emulators/re4-st3-firstpass-20261014/inventory.json'))}
tot = collections.Counter()
for r in sorted(inv):
    arc = sz('%s/rel33/rel-%s/st3/%s.arc' % (S, r, r)); dar = sz('%s/rel33/rel-%s/st3/%s.dar' % (S, r, r))
    w = sum(sz(f) for f in glob.glob('%s/tools/.assets/rooms-%s/rooms/%s/ps2-world.*' % (S, r, r)))
    ms = sz('%s/rel33/pkg-%s/MAINSCENARIO.re4mesh' % (S, r))
    evd = sum(sz(f) for f in glob.glob('/root/probe/lanes-20261014/st3/movies/movies-288x192-full/%s*/*.seq' % r))
    rooms[r] = dict(gc_das=inv[r]['gc_das'], ps2_dat=inv[r]['ps2_dat'], arc=arc, dar=dar, world=w, mainscen=ms, movies=evd)
    for k, v in rooms[r].items(): tot[k] += v or 0
for r, d in rooms.items(): print(r, d)
print('TOTAL', dict(tot))
# island texture keys not in the test 15 pak
def idx(p):
    b = open(p, 'rb').read(); m, v, c, io, do = struct.unpack_from('<8s4I', b, 0)
    return {struct.unpack_from('<2I', b, io + 16 * i): struct.unpack_from('<4I', b, io + 16 * i)[3] for i in range(c)}
a = idx(S + '/vq33/tex-st3vq4.pak'); b = idx('/root/probe/lanes-20261015/t15k/data/vq16cs/tex-vq16c.pak')
print('st3 pak keys', len(a), 'bytes', sum(a.values()), 'not in t15 pak', len([k for k in a if k not in b]), sum(v for k, v in a.items() if k not in b))
print('t15 pak bytes', sum(b.values()))
em = {}
for e in ('em1d', 'em1e', 'em1f'):
    em[e] = sz('%s/emprep/outT-%s/%s.drs' % (S, e, e)) + sum(sz(f) for f in glob.glob('%s/emprep/outT-%s/mot/*' % (S, e)))
print('prepared soldiers (drs + mot)', em)
mv = sum(sz(f) for f in glob.glob('/root/probe/lanes-20261014/st3/movies/movies-288x192-full/*/*.seq'))
print('island movies converted', len(glob.glob('/root/probe/lanes-20261014/st3/movies/movies-288x192-full/*/*.seq')), mv)
