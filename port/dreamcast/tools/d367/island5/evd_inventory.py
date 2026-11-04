import sys, os, hashlib, collections, json, struct
sys.path[:0] = ['/root/work/lanes/world-ch5/port/dreamcast/tools/d367/gc_port23']
import build_catalog as bc

# usage: evdinv.py OUTDIR disc:root [disc:root ...]
# Every event file on the discs: standalone evd/*.evd and the EVS bundles inside room archives (.dar/.das/.dat).
# Byte order is detected per file (be = GameCube raw, never converted).

def evd_parse(b):
    if len(b) < 0x50 or not b.startswith(b'event/'):
        return None, []
    for end, fmt in (('le', '<'), ('be', '>')):
        n, at = struct.unpack_from(fmt + '2I', b, 0x48)
        if n and n <= 4096 and 0x50 <= at and at + n * 0x40 <= len(b):
            ents = []
            for i in range(n):
                e = at + i * 0x40
                ents.append((b[e:e + 0x30].split(b'\0', 1)[0].decode('latin1'), struct.unpack_from(fmt + 'I', b, e + 0x30)[0]))
            offs = sorted({o for _, o in ents})
            out = []
            for name, o in ents:
                if at + n * 0x40 <= o < len(b):
                    out.append((name, o, next((q for q in offs if q > o), len(b)) - o))
            return end, out
    return None, []

def evs_spans(b, depth=0):
    for _i, tag, s, e in bc.archive_spans(b):
        if tag[:3] == b'EVS':
            yield s, b[s:e]
        elif depth < 3:
            for s2, sub in evs_spans(b[s:e], depth + 1):
                yield s + s2, sub

def evs_files(c):
    if len(c) < 8:
        return
    n, t = bc.word(c, 0), bc.word(c, 4)
    if not n or n > 256 or t < 8 or t > len(c) or 8 * n > len(c) - t:
        return
    offs = [bc.word(c, t + 8 * i) for i in range(n)]
    for o in offs:
        if t + 8 * n <= o < len(c):
            yield o, c[o:min([q for q in offs if q > o] + [len(c)])]

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
rows = []
def add(disc, where, b):
    order, ents = evd_parse(b)
    name0 = b[:0x20].split(b'\0', 1)[0].decode('latin1', 'replace')
    if not ents:
        rows.append((disc, where, name0, '-', 'unparsed', '-', 0, len(b), '')); return
    for name, o, size in ents:
        ext = name.rsplit('.', 1)[-1].lower() if '.' in name else '-'
        rows.append((disc, where, name0, name, ext, order, o, size, hashlib.sha256(b[o:o + size]).hexdigest()))

for spec in sys.argv[2:]:
    disc, root = spec.split(':', 1)
    for d, _, fs in os.walk(root):
        for f in sorted(fs):
            low = f.lower(); p = os.path.join(d, f); rel = os.path.relpath(p, root)
            if low.endswith('.evd'):
                add(disc, rel, open(p, 'rb').read())
            elif low.endswith(('.dar', '.das', '.dat')) and os.path.getsize(p) < 64 << 20:
                b = open(p, 'rb').read()
                bodies = [(0, b)] + [(at, body) for at, body in bc.record_bodies(b)]
                for at, body in bodies:
                    for s, evs in evs_spans(body):
                        for o, sub in evs_files(evs):
                            add(disc, '%s#EVS@%d+%d' % (rel, at + s, o), sub)

with open(os.path.join(out, 'evd-entries.tsv'), 'w') as fo:
    fo.write('disc\tcontainer\tevent\tentry\text\torder\toffset\tbytes\tsha256\n')
    for r in rows:
        fo.write('\t'.join(map(str, r)) + '\n')
KIND = {'bin': 'model', 'tpl': 'texture', 'seq': 'motion', 'fcv': 'motion', 'mdt': 'motion-data', 'eff': 'effect', 'lit': 'light'}
per = collections.defaultdict(collections.Counter); order = {}
for disc, where, ev, name, ext, o_, off, size, h in rows:
    k = KIND.get(ext, ext); per[(disc, where, ev)][k + '_n'] += 1; per[(disc, where, ev)][k + '_bytes'] += size
    order[(disc, where, ev)] = o_
kinds = sorted({k for c in per.values() for k in c})
with open(os.path.join(out, 'evd-files.tsv'), 'w') as fo:
    fo.write('disc\tcontainer\tevent\torder\t' + '\t'.join(kinds) + '\n')
    for key, c in sorted(per.items()):
        fo.write('%s\t%s\t%s\t%s\t%s\n' % (key[0], key[1], key[2], order[key], '\t'.join(str(c[k]) for k in kinds)))
tot = collections.defaultdict(collections.Counter); uniq = collections.defaultdict(set)
for key, c in per.items():
    tot[key[0]]['events'] += 1; tot[key[0]]['events_' + order[key]] += 1; tot[key[0]].update(c)
for disc, where, ev, name, ext, o_, off, size, h in rows:
    if ext == 'bin': uniq[disc].add(h)
summary = {d: dict(c, unique_models=len(uniq[d])) for d, c in tot.items()}
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1, sort_keys=True)
print(json.dumps(summary, indent=1, sort_keys=True))
