#!/usr/bin/env python3
"""items_census.py <ps2lib> <run-output.txt>...: GameCube fallbacks of lane items' classes at run time.

Reads the ITEMS_CENSUS=1 "itemcen: room= kind=itm|efm owner= id= nv= nn= nd=" lines (item_model.cpp / eff_sys.cpp)
and compares each model's signature with ps2lib/items and ps2lib/breakables manifest.json (ps2_items.py convert):
  PS2   the signature of the library's converted model (out_sig)
  GC    the GameCube signature (gc_sig) of a model the library converted: a GC fallback
  NONE  a model the library lists with ps2_source=NONE (no PS2 counterpart; drawn only if EFM_PS2_CUT is off)
  ?     not in the library for that room (another lane's EFF: enemy / weapon effects, other rooms)
Efm models registered by an ETM .eff (owner 0x55..0xBB) or the room EFF (owner 1) are matched by room + id;
core EFF ones (owner 0) by id against breakables/common. Prints one line per room and
"ITEMS-CENSUS PASS" (zero GC, at least one itm line) or FAIL; exit 1 on FAIL.
"""
import json
import re
import sys
from pathlib import Path

LINE = re.compile(r'itemcen: room=([0-9a-f]+) kind=(itm|efm) owner=([0-9a-f]+) id=([0-9a-f]+) nv=(\d+) nn=(\d+) nd=(\d+)')


def main():
    lib = Path(sys.argv[1])
    sigs = {}
    for cls in ('items', 'breakables'):
        for a in json.loads((lib / cls / 'manifest.json').read_text())['assets']:
            loc = a['locator']
            if loc['kind'] == 'ITM':
                key = ('itm', a['room'], loc['id'])
            elif loc['kind'] in ('EFF', 'ETM'):
                key = ('efm', a['room'], loc['id'])
            elif loc['kind'] == 'CORE':
                key = ('efm', 'core', loc['id'])
            else:
                continue
            sigs.setdefault(key, []).append(a)
    total = {'PS2': 0, 'GC': 0, 'NONE': 0, '?': 0}
    rooms = {}
    seen = set()
    for f in sys.argv[2:]:
        for m in LINE.finditer(Path(f).read_text(errors='replace')):
            room, kind, owner, idv = 'r' + m.group(1), m.group(2), int(m.group(3), 16), int(m.group(4), 16)
            sig = [int(m.group(5)), int(m.group(6)), int(m.group(7))]
            k = (f, room, kind, owner, idv)
            if k in seen:
                continue
            seen.add(k)
            cands = sigs.get((kind, 'core' if (kind == 'efm' and owner == 0) else room, idv), [])
            res = '?'
            for a in cands:
                if a['status'] == 'NONE' and sig == a['gc_sig']:
                    res = 'NONE'
                elif a['status'] == 'PS2' and sig == a['out_sig']:
                    res = 'PS2'
                elif sig == a['gc_sig'] and res != 'PS2':
                    res = 'GC'
            r = rooms.setdefault(room, {'PS2': 0, 'GC': 0, 'NONE': 0, '?': 0})
            r[res] += 1
            total[res] += 1
            if res == 'GC':
                print('GC fallback: %s %s owner=%02x id=%02x sig=%s' % (room, kind, owner, idv, sig))
    for room in sorted(rooms):
        print('items census: room=%s ps2=%d gc=%d none=%d other=%d' % (room, rooms[room]['PS2'], rooms[room]['GC'],
                                                                     rooms[room]['NONE'], rooms[room]['?']))
    ok = total['GC'] == 0 and total['PS2'] > 0
    print('ITEMS-CENSUS %s ps2=%d gc=%d none=%d other=%d' % ('PASS' if ok else 'FAIL', total['PS2'], total['GC'],
                                                            total['NONE'], total['?']))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
