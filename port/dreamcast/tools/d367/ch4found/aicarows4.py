"""aicarows4.py: lane ch4found16 chapter 4 rows for tools/aica_banks.py (ROOMS, ROOM_BGM0 and the ch4 stream preset),
the ch5found16 island method (aicarows.py)."""
import pathlib
p = pathlib.Path('/root/probe/lanes-20261016/ch4found/tree/port/dreamcast/tools/aica_banks.py')
t = p.read_text()

def sub(old, new):
    global t
    assert t.count(old) == 1, old[:60]
    t = t.replace(old, new)

sub("""    # r210 (St2, world coverage lane): no enemy archive (assets.sh discover r210: lists emleon03/04, no entries)
    'r210': ['st2/r210.dar'],
""", """    # r210 (St2, world coverage lane): no enemy archive (assets.sh discover r210: lists emleon03/04, no entries).
    # Ashley (pl11) is beside Leon here (lane ch4found16: cxc4cmW loads em/pl11.drs at entry).
    'r210': ['st2/r210.dar', 'em/pl11.drs'],
""")
sub("""    # r219 (St2, world coverage lane): no enemy archive (discover r219: emleon04.esl, no entries)
    'r219': ['st2/r219.dar'],
""", """    # r219 (St2, world coverage lane): no enemy archive (discover r219: emleon04.esl, no entries); Ashley (pl11) as r210
    'r219': ['st2/r219.dar', 'em/pl11.drs'],
""")
rows = [
    ('r211', ['em14']), ('r212', ['em11', 'pl11']), ('r213', ['em2d']), ('r214', ['em14', 'em1a', 'em25']), ('r215', []),
    ('r216', ['em3c']), ('r217', ['em11', 'em25']), ('r218', ['em1c']), ('r21b', ['em15']), ('r21d', ['em2d']),
    ('r220', ['em18']), ('r222', ['em11']), ('r223', ['em16']), ('r224', ['em2b']), ('r225', ['em13']),
    ('r226', ['em11']), ('r227', ['em14']), ('r229', ['em29', 'em18']), ('r22a', ['em18']), ('r22b', []),
]
old = "    # r40b (St4, follow-up 7): em1f (bringup inventory: em1f/em1f, st4_0)\n"
sub(old, """    # Chapter 4-1..4-4 (lane ch4found16, 2026-10-16): room .dar (lane rel31) + the room's enemies from the PS2 lists
    # (CH4-FOUNDATIONS-20261016.md cast list) + Ashley (pl11) where the runs load her (r210 r212 r219). The boss rooms
    # r221 (Verdugo, em2c) and r228 (Salazar, em38) are left to their owners (ch3found16 / cast16).
""" + ''.join("    '%s': ['st2/%s.dar'%s],\n" % (r, r, ''.join(", 'em/%s.drs'" % e for e in es)) for r, es in rows) + old)

sub("""             'r202': [8]}""", """             'r202': [8],
             # chapter 4 (lane ch4found16): bgm/bgmtbl.dat entry 0 slot-0 track (low byte), matched to the runtime's
             # "blk 3 (637,312 / 476,384 GC bytes) does not fit": #7 (r211 r213 r214 r226 r227 r22a), #14 (r210 r222
             # r224); r219 / r225 #5 and r21d / r229 #1 are already prebuilt (r108 / r102).
             'r211': [7], 'r213': [7], 'r214': [7], 'r226': [7], 'r227': [7], 'r22a': [7],
             'r210': [14], 'r222': [14], 'r224': [14], 'r219': [5], 'r225': [5], 'r21d': [1], 'r229': [1]}""")

old2 = "STREAM_PRESETS = {"
sub(old2, """# Chapter 4 (lane ch4found16, 2026-10-16): CH3_STREAMS (55) + chapter 4 would pass the 63-entry header, so chapter 4
# gets its own file, as the island disc does (ch5): the shared streams (0:0 death / continue, 0:29 results, the
# merchant's voice lines 1:180..1:194), every stream the chapter 4 rooms' bgm/bgmtbl.dat entries name (r210..r22b, all
# entries, blk 0) and the streams the first-pass runs logged as "not in aica_str.dat, silent" (cxc4cmW, Flycast):
# r218 0:31 (sbb 36f8000), r222 0:46 (5890000), r227 1:95 (5690000), r22b 1:135 (8f80000), r229 1:157 (a0e8000).
# `--streams ch4`; 39 entries (AICA_STR_ENT_MAX=56 holds it). Which disc carries it is the disc layout's call.
CH4_STREAMS = ([(0, 0), (0, 29)] + [(1, n) for n in range(0xB4, 0xC3)]
               + [(0, n) for n in (5, 13, 15, 16, 22, 25, 27, 31, 32, 33, 34, 35, 36, 37, 38, 47, 53, 56, 46)]
               + [(1, 95), (1, 135), (1, 157)])
""" + old2)
sub("'ch31': CH31_STREAMS, 'ch3': CH3_STREAMS}", "'ch31': CH31_STREAMS, 'ch3': CH3_STREAMS,\n                  'ch4': CH4_STREAMS}")
p.write_text(t)
print('ok', len(rows))
