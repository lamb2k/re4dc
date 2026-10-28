import sys
R = sys.argv[1] + '/port/dreamcast/tools/d367/rr/'
p = R + 'rr-cycle.sh'
s = open(p).read()
a = "  # EFFECT-CENSUS (lane fix-r100-props26 10-26): per route room"
assert s.count(a) == 1
s = s.replace(a, """  # MOTION-KEYS (lane cast-ps2-25 10-26): every dc/mot key a live MTC table of the candidate tree names exists in its dc/mot,
  # and the release fixture's remove list hits none of them (Test 25 r100 house siege: missing motion key halt).
  python3 "$TA/port/dreamcast/tools/d367/motion/mot_refs.py" "$W/rel/tree" --fixture "$W/pkg/fix/pkg-rr${S7}rP.json" \\
    --json "$W/motion-keys.json" > "$W/motion-keys.txt" 2>&1 || true
  tail -n 1 "$W/motion-keys.txt"
""" + a)
open(p, 'w').write(s)
p = R + 'rr-judge.py'
s = open(p).read()
a = "# EFFECT-CENSUS (lane fix-r100-props26 10-26): per-room effect-set counts"
assert s.count(a) == 1
s = s.replace(a, """# MOTION-KEYS (lane cast-ps2-25 10-26): rr-cycle.sh bases() runs motion/mot_refs.py over the candidate tree: a dc/mot key
# a live MTC table names but the disc lacks (or the fixture removes) halts the game on first use ("motion key read").
mk = rd(W / 'motion-keys.txt').strip().splitlines()
if mk:
    add('MOTION-KEYS', mk[-1].startswith('MOTION-KEYS PASS'),
        '; '.join([l for l in mk if not l.startswith(('MOTION-KEYS PASS', 'MOTION-KEYS note'))][:8] + [mk[-1]])[:600])

""" + a)
open(p, 'w').write(s)
print('ok')
