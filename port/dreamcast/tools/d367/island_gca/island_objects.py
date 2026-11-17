#!/usr/bin/env python3
"""island_objects.py OUTDIR [room...]  (lane island-gca round 3)
PS2 geometry for the Disc 3 island room objects, room by room, with ps2_objects.py room: every loose room BIN that is
le_mirror(GC BIN) and has a BIN at the same archive index in the PS2 rNNN.dat is paired (same index, the castle census rule),
every etc model is converted (--etm all). Input dars: island-d3 st3/*.dar (or the dar named in $DAR_<room>). GC rooms come from the
GC Disc 2 USA ISO. Output OUTDIR/<room>/<room>.dar + <room>.json and OUTDIR/summary.tsv."""
import json, os, subprocess, sys
from pathlib import Path
T = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(T)]
import ps2_objects as po  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402
rs, pb = po.rs, po.pb
GC2 = '/mnt/c/Game Dev/Emulators/Resident Evil 4 (USA) (Disc 2).iso'
PS2 = '/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso'
SRC = Path(os.environ.get('ISLAND_D3', '/root/re4data/private/island-d3-20261102'))
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
g = GcIso(GC2); idx = pb.afs_index(PS2)
rooms = sys.argv[2:] or sorted(p.stem for p in (SRC / 'st3').glob('r3*.dar'))
summ = []
for room in rooms:
    dar_p = os.environ.get('DAR_' + room, str(SRC / 'st3' / (room + '.dar')))
    dar = Path(dar_p).read_bytes()
    k, size, dest, off = __import__('struct').unpack_from('<4I', dar, 0x20)
    pay = dar[off:off + size]
    key = next((kk for rr, kk in g.rooms() if rr == room), None)
    if key is None:
        summ.append((room, 'no GC room')); continue
    gd = g.read(key)
    if gd[:32] == rs.CONTAINER_MAGIC:
        gd = rs.decode_das(gd)
    ge = rs.tagged_entries(gd, '>'); le = rs.tagged_entries(pay, '<')
    try:
        pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(PS2, room + '.dat', idx))}
    except Exception as ex:
        summ.append((room, 'no PS2 dat: %s' % ex)); continue
    pairs = []
    for i, (tag, s, e) in enumerate(ge):
        ga = i + 4
        if tag.rstrip(b'\0') != b'BIN' or i >= len(le) or le[i][0].rstrip(b'\0') != b'BIN' or ga not in pe or pe[ga][0] != 'BIN':
            continue
        cur = pay[le[i][1]:le[i][2]]
        try:
            if cur.rstrip(b'\0') == po.to_le(gd[s:e], '%x' % ga).rstrip(b'\0'):
                pairs.append('%x:%x' % (ga, ga))
        except Exception:
            pass
    od = out / room; od.mkdir(exist_ok=True)
    a = [sys.executable, str(T / 'ps2_objects.py'), 'room', '--dar', dar_p, '--room', room, '--etm', 'all', '--uv-fold', '--keep-larger',
         '--keep-larger-reason', 'no-GameCube-assets rule (user 10-23): the PS2 object replaces the GC one', '--out', str(od / (room + '.dar')),
         '--json', str(od / (room + '.json')), '--gc-iso', GC2, '--ps2-iso', PS2]
    if pairs:
        a += ['--pairs', ','.join(pairs)]
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode and 'IndexError' in r.stderr:   # a room whose ETM entry holds no models: no --etm
        a = [x for i, x in enumerate(a) if not (x == '--etm' or (i and a[i - 1] == '--etm'))]
        if not pairs:
            summ.append((room, 'no ETM models, no pairs: unchanged')); continue
        r = subprocess.run(a, capture_output=True, text=True)
    (od / 'objects.log').write_text(r.stdout + r.stderr)
    if r.returncode:
        summ.append((room, 'FAIL %s' % (r.stderr.strip().splitlines() or ['?'])[-1][:150])); continue
    j = json.load(open(od / (room + '.json')))
    # etc models whose PS2 model is a placeholder (one degenerate triangle): the PS2 draws nothing from that ETM entry (its world draws
    # the object), so the GC copy is emptied like the window panes. et0000 / et2500 are the panes (user: glass and bars): kept GC.
    ph = sorted({o['name'] for o in j['objects'] if o.get('kind') == 'etc' and 'placeholder' in (o.get('skipped') or '') and o['name'] not in ('et0000.bin', 'et2500.bin')})
    if ph:
        r = subprocess.run(a + ['--etm-empty', ','.join(ph)], capture_output=True, text=True)
        (od / 'objects.log').write_text(r.stdout + r.stderr)
        if r.returncode:
            summ.append((room, 'FAIL empty %s' % (r.stderr.strip().splitlines() or ['?'])[-1][:150])); continue
        j = json.load(open(od / (room + '.json')))
    ob = j['objects']; sk = [o for o in ob if o.get('skipped') and o.get('name') not in ph]
    summ.append((room, 'pairs %d objects %d converted %d skipped %d [%s] payload %+d' % (len(pairs), len(ob), len(ob) - len(sk), len(sk),
                 '; '.join('%s %s' % (o.get('name') or o.get('gc_arc'), o['skipped'][:50]) for o in sk), -j['payload_saved'])))
    print(room, summ[-1][1], flush=True)
(out / 'summary.tsv').write_text('\n'.join('%s\t%s' % x for x in summ) + '\n')
