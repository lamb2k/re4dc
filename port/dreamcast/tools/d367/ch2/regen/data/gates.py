"""gates.py EVIDENCE_DIR...: lane ch2regen gate table (WSL). Per run: rooms entered, HALT/FAULT/MISSING, TEX_CHECK totals,
'package absent' lines, CAST-GC verdict (tools/d367/cast_gc.py), and the 23 shadowed keys. A load line logs the runtime
format code only; the shadowed-key proof classifies each load of those keys by its (w, h, fmt) signature and compares it
with the tex.pak package and with the loose target file (payload kind 1 = 16-bit, 2 = VQ in the RE4DCTX entry): the
mapping fmt -> payload kind is learned from every other pak key the same log loaded."""
import collections, json, re, struct, subprocess, sys
L = '/root/probe/lanes-20261017r/ch2regen'
S = '/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen'
CG = L + '/t-int/port/dreamcast/tools/d367/cast_gc.py'
keys = [l.strip() for l in open(S + '/keys23.txt') if l.strip()]
def entry(b):
    t = struct.unpack_from('<I', b, 24)[0]
    _, w, h, fmt, off, size, flags, payload, extra = struct.unpack_from('<64s8I', b, t)
    return w, h, payload
pak = open(L + '/tex-13340bfa.pak', 'rb').read(); n, io = struct.unpack_from('<2I', pak, 12)
pk = {}
for i in range(n):
    c, f, o, z = struct.unpack_from('<4I', pak, io + 16 * i); pk['%08x-%08x' % (c, f)] = entry(pak[o:o + z])
need = json.load(open(S + '/need-n3.json'))['need']
loose_size = {p.split('/')[-1][:17]: need[p]['size'] for p in need if p.split('/')[-1][:17] in keys}
rows = []
for d in sys.argv[1:]:
    log = open(d + '/capture/run-output.txt', 'rb').read().decode('latin1')
    r = dict(run=d.rstrip('/').split('/')[-1])
    r['rooms'] = ','.join(dict.fromkeys(re.findall(r'room enter ([0-9a-f]+)', log)))
    for k, pat in (('halt', 'HALT'), ('missing', 'RE4DC MISSING'), ('fault', 'FAULT'), ('absent', 'package absent'), ('leongc', '\nLEONGC f=')):
        r[k] = log.count(pat)
    t = re.findall(r'texchk: frame=\d+ fails=(\d+) skips=(\d+) meta_changes=(\d+) vram_changes=(\d+) binds=(\d+)', log)
    r['texchk'] = 'fails=%s skips=%s meta=%s vram=%s binds=%s' % t[-1] if t else 'NO COVERAGE'
    p = subprocess.run(['python3', CG, d + '/capture/run-output.txt'], capture_output=True, text=True)
    r['castgc'] = {0: 'PASS', 1: 'FAIL', 2: 'NO CENSUS'}.get(p.returncode, 'rc%d' % p.returncode)
    r['castgc_detail'] = [l for l in p.stdout.splitlines() if ' GC' in l or 'MIXED' in l or 'FAIL' in l][:8]
    loads = re.findall(r'native UI: load /cd/dc/tex/[0-9a-f]/([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)', log)
    fmap = collections.defaultdict(set)
    for k, w, h, fm in loads:
        if k in pk and k not in keys: fmap[int(fm)].add(pk[k][2])
    r['fmt_map'] = {f: sorted(v) for f, v in sorted(fmap.items())}
    seen = []
    for k, w, h, fm in loads:
        if k not in keys: continue
        kinds = fmap.get(int(fm), set())
        pak_kind = pk[k][2]; loose_kind = 2 if loose_size.get(k, 0) < pk[k][0] * pk[k][1] * 2 else 1
        verdict = 'pak' if kinds == {pak_kind} and pak_kind != loose_kind else ('LOOSE?' if kinds == {loose_kind} and pak_kind != loose_kind else 'ambiguous')
        seen.append('%s %sx%s fmt=%s pak_kind=%d loose_kind=%d -> %s' % (k, w, h, fm, pak_kind, loose_kind, verdict))
    r['keys23'] = seen
    rows.append(r); print(json.dumps(r))
json.dump(rows, open(S + '/gates-last.json', 'w'), indent=1)
