#!/usr/bin/env python3
# summ.py <harness> <suffix> [rooms]: per-run summary from rfp-result.json + run-output.txt (Windows python).
import json, re, sys, glob, os
H = r'C:\Flycast-Evidence\re4-dreamcast\ch4found-20261016' + '\\' + sys.argv[1]
suf = sys.argv[2]
rows = []
for d in sorted(glob.glob(H + r'\scenarios\cx-r*-walk-' + suf)):
    name = os.path.basename(d); room = name.split('-')[1]
    if len(sys.argv) > 3 and room not in sys.argv[3:]:
        continue
    res = {}
    try:
        res = json.load(open(d + r'\rfp-result.json'))
    except Exception:
        pass
    log = ''
    try:
        log = open(d + r'\capture\run-output.txt', 'rb').read().decode('latin1')
    except Exception:
        pass
    L = log.splitlines()
    def grab(pat, n=3):
        return [l.strip()[:220] for l in L if re.search(pat, l)][:n]
    entry = grab(r'warp: room enter', 2)
    halts = grab(r'HALT|FAULT|RE4DC MISSING|OSPanic|MISALIGN|link failed|not in the image', 4)
    heap = grab(r'heap4 census|HEAP4_WATER|heap4 low|heap 4 low', 3)
    refuse = grab(r'alloc\[.*free\[|refused|does not fit|Mem Alloc|DVD: Mem', 6)
    vram = [l for l in L if 'VRAM_ROOM' in l or 'vram room' in l.lower()]
    alive = grab(r'alivecap', 4)
    nmrs = grab(r'NMRS .*declined=[1-9]|NMRM decline|NMRPACK refuse', 3)
    fps = grab(r'fps=|pace: ', 2)
    texfail = len([l for l in L if 'texchk: FAIL' in l])
    em = sorted(set(re.findall(r'em/(em[0-9a-f]{2})\.drs', log)))
    print('==', room, res.get('overall'), res.get('checks'), 'aica_nofit=%d' % len(res.get('aica_does_not_fit', [])), 'texfail=%d' % texfail)
    for k, v in (('entry', entry), ('halt', halts), ('heap', heap), ('refuse', refuse), ('vram', vram[-2:]), ('alive', alive), ('nmrs', nmrs), ('em', em)):
        if v:
            print('   %s: %s' % (k, v if isinstance(v, list) else v))
