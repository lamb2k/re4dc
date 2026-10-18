"""aicarows.py: lane ch5found16 island rows for tools/aica_banks.py (ROOMS, ROOM_BGM0 and the ch5 stream preset)."""
import pathlib, sys
p = pathlib.Path('/root/probe/lanes-20261016/ch5found/tree/port/dreamcast/tools/aica_banks.py')
t = p.read_text()
old = """    'r300': ['st3/r300.dar', 'em/em1d.drs'],
    'r301': ['st3/r301.dar', 'em/em1e.drs', 'em/em3b.drs'],
    'r303': ['st3/r303.dar', 'em/em1e.drs'],
"""
assert t.count(old) == 1
rows = [
    ('r304', ['em1f', 'em25']), ('r305', ['em1e']), ('r306', ['em36']), ('r307', ['em36']), ('r308', ['em36']),
    ('r30b', ['em1f', 'pl11']), ('r30c', ['em1f', 'em25', 'pl11']), ('r30e', ['em1e', 'pl11']), ('r309', ['em36', 'pl11']),
    ('r30a', ['em18', 'em23', 'pl11']), ('r310', ['em36', 'pl11']), ('r311', ['em1f', 'pl11']), ('r30d', ['em36', 'pl11']),
    ('r312', ['em18', 'pl11']), ('r30f', ['em1f', 'pl11']), ('r315', ['em1e', 'pl11']), ('r316', ['em1e', 'pl11']),
    ('r317', []), ('r318', []), ('r31a', ['em18']), ('r31b', ['em32']), ('r31d', ['em1e']), ('r31c', ['em39', 'em3a']),
    ('r320', ['em1d', 'em3d']), ('r321', ['em1f']), ('r325', []), ('r326', ['em36']), ('r327', ['em1d']),
    ('r329', ['em18', 'pl11']), ('r330', ['em1f', 'pl11']),
]
DROP = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else set()   # enemy archives the build cannot read yet
new = old + """    # Island chapters 5-1..5-4 (lane ch5found16, 2026-10-16): room .dar (st3 lane rel33) + the room's enemies from the
    # PS2 lists (ISLAND-ROUTE-20261016.md) + Ashley (pl11) from her rescue in r30c to r316 and again from r329.
""" + ''.join("    '%s': ['st3/%s.dar'%s],\n" % (r, r, ''.join(", 'em/%s.drs'" % e for e in es if e not in DROP))
              for r, es in rows)
if DROP:
    new += "    # not listed yet (no prepared archive the tool can read): %s\n" % ', '.join(sorted(DROP))
t = t.replace(old, new)

streams = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else '1:159,1:230,1:233,1:234,1:238'
ISL0 = '0x14, 0x27, 0x39, 0x34, 0x1A, 0x29, 0x28, 0x03, 0x30, 0x19, 0x2A, 0x2B, 0x2C, 0x2D, 0x3B'
lst = ', '.join('(%s, %s)' % tuple(s.split(':')) for s in streams.split(','))
n = 2 + 15 + len(ISL0.split(',')) + len(streams.split(','))
old2 = "STREAM_PRESETS = {"
assert t.count(old2) == 1
pre = (
    "# The island disc (lane ch5found16, 2026-10-16; three-disc layout, user decision: disc 3 = island + final chapter).\n"
    "# Disc 3 carries its own bgm/aica_str.dat (streams are found by sbb offset, so the order is free): the shared\n"
    "# streams (0:0 death / continue, 0:29 results, the merchant's voice lines 1:180..1:194), every room stream the island\n"
    "# rooms' bgm/bgmtbl.dat entries name (r300..r330, blk 0) and the event / voice streams the first-pass runs logged as\n"
    "# \"not in aica_str.dat, silent\" (cx5cmW, Flycast). `--streams ch5`; %d entries, so AICA_STR_ENT_MAX=56 holds it.\n"
    "CH5_STREAMS = ([(0, 0), (0, 29)] + [(1, n) for n in range(0xB4, 0xC3)]\n"
    "               + [(0, n) for n in (%s)]\n"
    "               + [%s])\n" % (n, ISL0, lst))
t = t.replace(old2, pre + old2)
t = t.replace("'ch31': CH31_STREAMS, 'ch3': CH3_STREAMS}", "'ch31': CH31_STREAMS, 'ch3': CH3_STREAMS, 'ch5': CH5_STREAMS}")
assert "'ch5': CH5_STREAMS" in t

old3 = "             'r202': [8]}"
assert t.count(old3) == 1
bgm7 = ', '.join("'%s': [7]" % r for r in ('r300', 'r301', 'r30a', 'r31c', 'r31d', 'r320', 'r321', 'r325', 'r327', 'r329'))
new3 = ("             'r202': [8],\n"
        "             # island (lane ch5found16): bgm/bgmtbl.dat slot-0 track of each room's entry 0 (the runtime's \"blk 3\"\n"
        "             # sizes 637,312 / 476,384 matched): #7 (637,306 GC bytes), r311 #14, r315 #5, r31a / r31b #1\n"
        "             " + bgm7 + ",\n"
        "             'r311': [14], 'r315': [5], 'r31a': [1], 'r31b': [1]}")
t = t.replace(old3, new3)
p.write_text(t)
print('ok', len(rows), 'rows', n, 'streams')
