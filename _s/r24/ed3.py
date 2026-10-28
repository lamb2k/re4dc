import sys, shutil
R = sys.argv[1] + '/port/dreamcast/tools/d367/rr/'
open(R + 'siege-r100-warp.txt', 'w').write(open(sys.argv[2]).read().replace('\r', ''))
p = R + 'rr-jobs.sh'
s = open(p).read()
a = 'echo "$(census_rooms)" > "$W/census-rooms.txt"\n'
assert s.count(a) == 1
s = s.replace(a, a + '''# siege (lane cast-ps2-25 10-26): the r100 house siege (bench-r100-house: rsf 0x100 13, scenario 0x10, the village
# alerted, Ganados close in) on every tier. It halted Test 25 candidates on a dc/mot key a stale enemy archive streamed;
# rr-judge.py fails on HALT / FAULT / RE4DC MISSING in its log.
tr -d '\\r' < "$T/port/dreamcast/tools/d367/rr/siege-r100-warp.txt" > "$EVU/fixtures/siege-r100.txt"
job 1 siege-r100 "$(run siege-r100 c c 60 --warp "\\"\\$EVW\\\\fixtures\\\\siege-r100.txt\\"")"
''')
open(p, 'w').write(s)
p = R + 'rr-judge.py'
s = open(p).read()
a = "    for n, _, _, rc in jobs:\n        if n.startswith('cap-'):"
assert s.count(a) == 1
s = s.replace(a, """    # siege (lane cast-ps2-25 10-26): r100 house siege, Ganados streaming their motion (rr-jobs.sh siege-r100)
    sg = EVU / 'siege-r100' / 'run-output.txt'
    if 'siege-r100' in [j[0] for j in jobs] or sg.exists():
        so = sg.read_text(errors='replace').replace('\\x00', '') if sg.exists() else ''
        sb = sorted(set(m.group(0)[:80] for m in re.finditer(r'(HALT|FAULT|RE4DC MISSING|Out of memory)[^\\n]*', so)))
        add('siege r100 HALT/FAULT/MISSING 0', bool(so) and 'warp: placed room=100' in so and not sb,
            ('no log' if not so else ('not placed' if 'warp: placed room=100' not in so else ('none' if not sb else '; '.join(sb[:4])))))
""" + a)
open(p, 'w').write(s)
print('ok')
