# --- chapter 2-2 content (route lane ch22), inserted by mkc22fix.sh into a copy of test9/t9-fix.py ---
# C22=0 in the environment leaves it out (a CH22-off fixture of the same arm).
C22R = pathlib.Path('/root/probe/lanes-20261013/ch22w/rooms')
C22_ROOMS = [x for x in os.environ.get('C22_ROOMS', 'r112 r111 r113').split() if x]
if os.environ.get('C22', '1') == '1':
    added = 0
    for rr in C22_ROOMS:
        r['st1/%s.arc' % rr] = str(C22R / ('rel-%s/st1/%s.arc' % (rr, rr)))
        r['st1/%s.dar' % rr] = str(C22R / ('aica-c22/st1/%s.dar' % rr))
        r['dc/native/%s/MAINSCENARIO.re4mesh' % rr] = str(C22R / ('pkg-%s/MAINSCENARIO.re4mesh' % rr))
        for n in ('ps2-world.r4pw', 'ps2-world.re4mesh', 'ps2-world.ids'):
            r['dc/native/%s/%s' % (rr, n)] = str(C22R / ('%s-ps2' % rr) / n)
    # the chapter 2-2 banks: bio4midi #6 prebuilt, em17's bank at the route plan's cap; the ch22 stream file
    r['bgm/bio4midi.dat'] = str(C22R / 'aica-c22/bgm/bio4midi.dat')
    r['em/em17.drs'] = str(C22R / 'aica-c22/em/em17.drs')
    r['bgm/aica_str.dat'] = str(C22R / 'str-c22/bgm/aica_str.dat')
    dirs = []
    for rr in C22_ROOMS:
        dirs += [C22R / ('tex-%s-vq' % rr), C22R / ('pairs-%s' % rr), C22R / ('tex-%s' % rr), C22R / ('%s-ps2/tex' % rr)]
    for t in dirs:
        if not t.is_dir():
            continue
        for p in sorted(t.glob('*.re4tex')):
            k = 'dc/tex/%s/%s' % (p.name[0], p.name)
            if k not in r:
                r[k] = str(p)
                added += 1
    d['provenance']['ch22'] = dict(rooms=C22_ROOMS, textures_loose=added, dir=str(C22R))
