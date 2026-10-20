#!/usr/bin/env python3
"""qa20/mkqa.py (lane qa20): the QA disc's teleport presets (QA_MENU=1, game/qamenu.mk).

Writes <out>/menu.txt and one fixture per preset (<out>/<id>.txt); the disc carries them as /cd/dc/qa/.
Sources (no new states are invented here):
  - castgc/warps/<room>.txt: the CAST-GC census fixtures (each puts a route room in a play state with its enemies alive);
  - fullplay/segments/lake-warp.txt: the Del Lago fight (trg 1) and, with its kill line, the night shore after it (#43);
  - benchpub/scene1-warp.txt: the r101 cross benchmark view; qa20/src/farm-midfight.txt (from scenario19) (r103 farm fight);
  - stage_route.py door entries (dstPos / dstAngle) for route rooms without a census fixture (bare jumps).
Lines only a measurement needs are dropped (god, alivelog, census, act, kill, bench, alert, dump, stills): the menu's
toggles own invincibility, and the player owns the pad.
Usage: mkqa.py <out dir> [--sr1 <stage_route --stage 1 --json file>]"""
import json, re, subprocess, sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent          # tools/d367
DROP = re.compile(r'^(god|alivelog|census|act|act_clock|kill|killrep|killnear|killpart|bench|alert|dump|freeze|still|'
                  r'shot|quit|stop|viewdist|face|bring|handpose|lookstep|charbake|lodat|late|name)\b')


def fixture(src, keep_kill=False):
    out = []
    for l in (D / src).read_text().splitlines():
        s = l.split('#', 1)[0].strip()
        if not s:
            continue
        if keep_kill and re.match(r'^(kill)\b', s):
            out.append(s)
            continue
        if DROP.match(s):
            continue
        out.append(s)
    return out


def door_entry(sr, room):
    for src, r in sorted(sr.items()):
        for d in r['doors']:
            if d['dst'] == room and src != room:
                return ['room 0x%s' % room[1:], 'pos %d %d %d' % tuple(d['pos']), 'ang %.3f' % d['angle'], 'inv default']
    return None


def main():
    out = Path(sys.argv[1])
    sr1 = sys.argv[sys.argv.index('--sr1') + 1] if '--sr1' in sys.argv else None
    if not sr1:
        sr1 = str(out.parent / 'sr1.json')
        subprocess.run([sys.executable, str(D / 'stage_route.py'), '--stage', '1', '--json', sr1], check=True,
                       stdout=subprocess.DEVNULL)
    sr = json.load(open(sr1))['rooms']
    cg = lambda r: fixture('castgc/warps/%s.txt' % r)
    lake = 'fullplay/segments/lake-warp.txt'
    # (chapter, [(id, kind, label, lines)])
    menu = [
        ('CHAPTER 1-1: VILLAGE', [
            ('r100', 'S', 'R100 FOREST PATH (HOUSE, AFTER S20)', cg('r100')),
            ('r101', 'S', 'R101 VILLAGE SQUARE (FIGHT START)', cg('r101')),
            ('r101x', 'S', 'R101 VILLAGE SQUARE, BY THE CROSS', fixture('benchpub/scene1-warp.txt')),
            ('r102', 'S', 'R102 ENTRY', cg('r102')),
            ('r103', 'S', 'R103 FARM (ENTRY)', cg('r103')),
            ('r103f', 'S', 'R103 FARM FIGHT (ONE DOWN)', fixture('qa20/src/farm-midfight.txt', keep_kill=True)),
            ('r104', 'S', 'R104 ENTRY', cg('r104')),
            ('r105', 'S', 'R105 ENTRY', cg('r105')),
            ('r106', 'S', 'R106 ENTRY', cg('r106')),
            ('r107', 'S', 'R107 ENTRY', cg('r107')),
        ]),
        ('CHAPTER 1-2', [
            ('r108', 'S', 'R108 ENTRY', cg('r108')),
            ('r109', 'S', 'R109 ENTRY', cg('r109')),
            ('r10a', 'S', 'R10A ENTRY', cg('r10a')),
            ('r117', 'S', 'R117 ENTRY', cg('r117')),
            ('r118', 'S', 'R118 ENTRY', cg('r118')),
            ('r119', 'S', 'R119 EL GIGANTE (FIGHT)', cg('r119')),
        ]),
        ('CHAPTER 1-3: LAKE', [
            ('r10b', 'S', 'R10B LAKE SHORE, BOAT START', cg('r10b')),
            ('r10bd', 'S', 'R10B DEL LAGO FIGHT', [l for l in fixture(lake) if not l.startswith('census')]),
            ('r11bn', 'S', 'R11B NIGHT SHORE AFTER DEL LAGO', fixture(lake, keep_kill=True)),
            ('r11b', 'S', 'R11B NIGHT SHORE (WALK)', cg('r11b')),
            ('r11a', 'S', 'R11A ENTRY', cg('r11a')),
        ]),
        ('CHAPTER 2-1: DAM', [
            ('r10c', 'S', 'R10C DAM', cg('r10c')),
            ('r10d', 'B', 'R10D DAM SIDE ROOM (DOOR ENTRY)', door_entry(sr, 'r10d')),
            ('r10e', 'S', 'R10E DAM', cg('r10e')),
            ('r10f', 'S', 'R10F ENTRY', cg('r10f')),
        ]),
        ('CHAPTER 2-2', [
            ('r111', 'S', 'R111 ENTRY', cg('r111')),
            ('r112', 'S', 'R112 ENTRY', cg('r112')),
            ('r113', 'S', 'R113 ENTRY', cg('r113')),
            ('r11c', 'S', 'R11C CABIN', cg('r11c')),
        ]),
        ('CHAPTER 2-3', [
            ('r11d', 'S', 'R11D ENTRY', cg('r11d')),
            ('r11e', 'S', 'R11E EL GIGANTE (FIGHT)', cg('r11e')),
            ('r11f', 'S', 'R11F ENTRY', cg('r11f')),
            ('r200', 'S', 'R200 CASTLE GATE', cg('r200')),
        ]),
    ]
    out.mkdir(parents=True, exist_ok=True)
    lines = ['# QA disc presets (tools/d367/qa20/mkqa.py)']
    for ch, ps in menu:
        lines.append('ch ' + ch)
        for pid, kind, label, body in ps:
            if not body:
                print('skip %s: no state source' % pid, file=sys.stderr)
                continue
            (out / (pid + '.txt')).write_text('\n'.join(['# QA preset %s: %s' % (pid, label)] + body) + '\n')
            lines.append('p %s.txt %s %s' % (pid, kind, label))
    (out / 'menu.txt').write_text('\n'.join(lines) + '\n')
    print('mkqa: %d presets in %s' % (sum(1 for l in lines if l.startswith('p ')), out))


main()
