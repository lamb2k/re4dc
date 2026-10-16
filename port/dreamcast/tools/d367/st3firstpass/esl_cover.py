"""Stage-3 enemy coverage per room from the GC and PS2 lists 6 / 7 (offline, list data only)."""
import collections, json, struct
F = "BBBBIHBB3h3hHh4s"
GC = '/root/probe/lanes-20261014/st3/deps/source/etc/emleon%02d.esl'        # GC disc 2, big-endian
PS = '/root/probe/lanes-20261014/st3/ps2-esl/emleon%02d.esl'               # PS2 USA, little-endian
GANADO = set(range(0x10, 0x21))  # Ganado / soldier ids (ACT_CAP's class): em1d / em1e / em1f here
NAMES = {0x1d: 'soldier', 0x1e: 'soldier', 0x1f: 'ganado', 0x18: 'merchant', 0x23: 'crow', 0x25: 'em25',
         0x36: 'em36 (lab creature)', 0x3b: 'vehicle', 0x3d: 'em3d', 0x32: 'em32 (boss)', 0x39: 'em39', 0x3a: 'em3a',
         0x31: 'em31 (boss)', 0x0e: 'em0e', 0x11: 'em11', 0x00: 'em00 (item/object)'}
out = collections.defaultdict(lambda: dict(gc=collections.Counter(), ps=collections.Counter(), gc_alive=0, ps_alive=0,
                                            gc_alive_g=0, ps_alive_g=0, gc_hp=[], ps_hp=[], diffs=0))
for n in (6, 7):
    g = list(struct.iter_unpack('>' + F, open(GC % n, 'rb').read()))
    p = list(struct.iter_unpack('<' + F, open(PS % n, 'rb').read()))
    for a, b in zip(g, p):
        for side, r, E in (('gc', a, '>'), ('ps', b, '<')):
            if r[1] == 0 and r[14] == 0:
                continue
            o = out[r[14]]
            o[side][r[1]] += 1
            if r[0] & 1:
                o[side + '_alive'] += 1
                if r[1] in GANADO:
                    o[side + '_alive_g'] += 1
        if a != b:
            out[a[14] if a[1] else b[14]]['diffs'] += 1
rows = []
for room in sorted(out):
    o = out[room]
    if not (0x300 <= room <= 0x334):
        continue
    ids = sorted(set(o['gc']) | set(o['ps']))
    rows.append(dict(room='r%03x' % room,
                     ps2_entries=' '.join('em%02x:%d' % (i, o['ps'][i]) for i in ids if o['ps'][i]),
                     gc_entries=' '.join('em%02x:%d' % (i, o['gc'][i]) for i in ids if o['gc'][i]),
                     gc_start_alive=o['gc_alive'], ps2_start_alive=o['ps_alive'],
                     ps2_start_alive_ganado=o['ps_alive_g'], ps2_ganado_entries=sum(o['ps'][i] for i in ids if i in GANADO),
                     rows_changed=o['diffs'],
                     classes=sorted({NAMES.get(i, 'em%02x' % i) for i in ids})))
print(json.dumps(rows, indent=1))
