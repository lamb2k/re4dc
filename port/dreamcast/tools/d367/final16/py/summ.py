"""summ.py <run-output.txt>...: lane final16 per-run summary (Flycast): phases by room frame, heap 4 water, VRAM, KOS, AICA,
pacing, motion misses, Saddler state (emlog), movie lines."""
import re, sys
for path in sys.argv[1:]:
    t = open(path, encoding='latin-1').read().split('\n')
    name = path.replace('\\', '/').split('/scenarios/')[-1].split('/')[0]
    h4 = [(int(m.group(1)), int(m.group(2))) for l in t for m in [re.search(r'heap4 water: room 332 free (\d+) largest (\d+)', l)] if m]
    vr = [l for l in t if l.startswith('vram room: r=332')]
    kos = [int(m.group(1)) for l in t for m in [re.search(r'vram gaps: r=332 .* kos=(\d+)', l)] if m]
    kosf = [int(m.group(1)) for l in t for m in [re.search(r'kos_free=(\d+)', l)] if m]
    pace = [l for l in t if l.startswith('PACE t=')]
    miss = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for l in t for m in [re.search(r'motion miss #(\d+): archive=\d+ entry=(\d+) bytes=\d+ wait_us=(\d+)', l)] if m]
    em = [l for l in t if 'warp: emlog 31 frame' in l and 'type=0' in l]
    hits = [l for l in t if 'warp: emlog pl frame' in l]
    print('==', name)
    if h4:
        print(' heap4: min free %d (largest %d at that point); min largest %d; last free %d' % (min(h4)[0], min(h4)[1], min(x[1] for x in h4), h4[-1][0]))
    for l in vr:
        m = re.search(r'at=(\w+) f=(\d+) .*pinned=(\d+) dynamic=(\d+) other=(\d+) free=(\d+) largest=(\d+) min_free=(\d+) min_largest=(\d+) peak_pinned=(\d+) loads=(\d+) evicted=(\d+)', l)
        if m: print(' vram %s f=%s pinned=%s dynamic=%s free=%s largest=%s min_free=%s peak_pinned=%s loads=%s evicted=%s' % (m.groups()[0:2] + m.groups()[2:4] + m.groups()[5:7] + (m.group(8), m.group(10), m.group(11), m.group(12))))
    if kos: print(' kos (vram gaps) min %d' % min(kos))
    if kosf: print(' kos_free (movie lines) min %d' % min(kosf))
    for l in t:
        if 'snd_used=' in l and 'vram gaps: r=332' in l:
            snd = re.search(r'snd_fail=(\d+) snd_used=(\d+)', l).groups()
    try: print(' aica snd_fail=%s used=%s' % snd)
    except NameError: pass
    for l in pace: print(' ' + ' '.join(x for x in l.split() if x.split('=')[0] in ('t', 'drawn', 'skip', 'fps', 'speed', 'draw_us', 'skip_us')))
    if miss:
        print(' motion misses %d, wait total %.2f s, max %.0f ms, entries %s' % (len(miss), sum(x[2] for x in miss) / 1e6, max(x[2] for x in miss) / 1e3, sorted({x[1] for x in miss})))
    if em:
        r1 = []
        for l in em:
            m = re.search(r'hp=(-?\d+) r=(\d+)/(\d+)/(\d+)/(\d+)', l)
            if m and (not r1 or r1[-1] != m.group(2, 3)): r1.append(m.group(2, 3))
        print(' saddler hp %s -> %s; routines r0/r1 seq %s' % (re.search(r'hp=(-?\d+)', em[0]).group(1), re.search(r'hp=(-?\d+)', em[-1]).group(1), ' '.join('/'.join(x) for x in r1)))
    if hits:
        print(' leon ' + re.search(r'total=\S+', hits[-1]).group(0) + ' (hits/damage god mode undid)')
    esp = sum(1 for l in t if l.startswith('ESP : num max'))
    if esp: print(' ESP effect pool full lines: %d' % esp)
    for l in t:
        if l.startswith('CRASH_SCREEN'): continue
        if re.search(r'route movie (start|skip|terminal)|not in aica|does not fit|MISSING|halt|NMR preload skip', l): print(' ' + l[:170])
