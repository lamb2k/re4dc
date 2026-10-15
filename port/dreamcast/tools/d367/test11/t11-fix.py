#!/usr/bin/env python3
"""t11-fix.py NEW_LABEL OUT.json [--data a,b,...] [--set DEST=SRC]... [--rm DEST]... [--texdir DIR]...
              [--warp FILE] [--pad FILE] [--qtxt FILE] [--base FIXTURE --base-label LABEL]
Test 11 fixtures: a copy of the test 10 package fixture (test10s fix/pkg-t10stP.json: the 9.1 fixture + the GC-atlas
tex.pak + the hands package) with the program label swapped and the test 11 data added.
  --data NAMES  named test 11 data sets (DATA below; each is disc data only, staged by the recipe)
  --set D=S     stage file S at disc path D (replaces); --rm D drops D from the disc
  --texdir DIR  every <crc>-<fnv>.re4tex under DIR as a loose dc/tex/<c>/<name> (the runtime reads a key that is not
                in dc/tex.pak from its loose file; native_ui.cpp texpack kNotInPack)
Every staged file must exist; its sha256 prefix is recorded in provenance.t11."""
import json, sys, hashlib, os, re
from pathlib import Path

BASE = '/root/probe/lanes-20261014/t10s/fix/pkg-t10stP.json'
BASE_LABEL = 't10stP'
PRIV = '/mnt/c/Game Dev/Emulators/re4-assets-private'
T11D = '/root/probe/lanes-20261014/t11/data'
# Named data sets: disc path -> source (a directory value under 'tex' = loose textures). Filled in as each is proven.
DATA = {
    # A1 r119 dark block: the r119 objects package with only the BIN 0x22 pair (docs/lanes/look.md section 2)
    'r119c': {'st1/r119.dar': PRIV + '/look-20261013/r119c/r119.dar'},
    # A2 r106 bats (em29): Codex's composite pair package (color 8721b93e-a420c9ed, mask c3ad3454-e7b41714;
    # codex-ps2-assets-20261013/r106-em29-v1), missing from the test 10 disc
    'em29': {'dc/tex/b/b8420096-5d9dc3c4.re4tex': PRIV + '/t11-20261014/pairs/b8420096-5d9dc3c4.re4tex'},
    # A3 chapter 2-1 results picture: pair color c050cf4e-216cd784 + mask ec97f64b-dab43d54 (em11.drs, built by lane
    # r117 pairs-em11 on 10-10 and never staged)
    'fbec': {'dc/tex/f/fbec854a-b7656a09.re4tex': PRIV + '/t11-20261014/pairs/fbec854a-b7656a09.re4tex'},
    # A4 r100 SMX + tr4 overlays (needs game PS2_R100_SMX=1 PS2_R100_TR4=1: the interior cell checks the package CRCs)
    'r100tr4': {'dc/native/r100/ps2-world.re4mesh': PRIV + '/t11-20261014/r100-smx-tr4/ps2-world.re4mesh',
                'dc/native/r100/ps2-world.r4pw': PRIV + '/t11-20261014/r100-smx-tr4/ps2-world.r4pw',
                'dc/native/r100/ps2-world.ids': PRIV + '/t11-20261014/r100-smx-tr4/ps2-world.ids',
                'dc/native/r100/interior.cell': PRIV + '/t11-20261014/r100-smx-tr4/interior.cell',
                'tex': PRIV + '/t11-20261014/r100-smx-tr4/tex'},
    # A5 Codex SMX-only meshes (asset-only-smx-r103-r101-v1: sidecar, ids and textures byte-identical to the staged ones)
    'smx101': {'dc/native/r101/ps2-world.re4mesh': PRIV + '/t11-20261014/r101-smx/ps2-world.re4mesh'},
    'smx103': {'dc/native/r103/ps2-world.re4mesh': PRIV + '/t11-20261014/r103-smx/ps2-world.re4mesh'},
    # A6 r10b with --cutout-max-alpha 224 (p2pt-cutout-20261012/r10b = the audit rebuild; mesh unchanged, its 3 cutout
    # textures are already in tex.pak)
    'r10bcut': {'dc/native/r10b/ps2-world.r4pw': PRIV + '/t11-20261014/r10b-cut/ps2-world.r4pw',
                'dc/native/r10b/ps2-world.ids': PRIV + '/t11-20261014/r10b-cut/ps2-world.ids'},
}
ALL_A = 'r119c,em29,fbec,r100tr4,smx101,smx103,r10bcut'
# D black faces (lane t11-bk, docs/lanes/t11-bk.md): the 0xa0000000 scenery BINs lit offline. blackps2 = the PS2 run-time
# rule measured in PCSX2 (--a0-light ps2, default); blackgc = the GameCube static room lights (--a0-light gc). 15 rooms
# (r102-r10b, r117-r11b; not r100 / r101). Each set's r10b is built with cutout 224 and its r103 with the SMX rule, so it
# replaces r10bcut / smx103 (do not stage those with it). Re-keyed textures are loose files (newtex).
BLACK_ROOMS = 'r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r117 r118 r119 r11a r11b'.split()
for _s in ('blackps2', 'blackgc'):
    DATA[_s] = {'dc/native/%s/ps2-world.%s' % (r, x): PRIV + '/t11-20261014/%s/%s/ps2-world.%s' % (_s, r, x)
                for r in BLACK_ROOMS for x in ('re4mesh', 'r4pw', 'ids')}
    DATA[_s]['tex'] = PRIV + '/t11-20261014/%s/newtex' % _s
# blackgc14 = blackgc without r119: the GC bake grows r119's mesh by 184,832 B (1,058,272 -> 1,243,104; heap 4) and
# the El Gigante end movies 11930 / 11920 then fail their heap-4 staging (c-g3, 10-14). r119 keeps the test 10 package.
DATA['blackgc14'] = {k: v for k, v in DATA['blackgc'].items() if not k.startswith('dc/native/r119/')}
# blackgc14p = blackgc14 with its 424 re-keyed textures inside tex.pak instead of loose files, plus Leon's 2x packages
# (tex-t11.pak = tex-gcatlas-hr.pak + blackgc/newtex, texpack.py, 4311 packages, sha256 1582e5c5). Loose, they stopped
# the r117 Playing Manual 3 file being given after s00 (full-play t11a ch21; bisect c3/c6/c7/c8, 10-14).
DATA['blackgc14p'] = {k: v for k, v in DATA['blackgc14'].items() if k != 'tex'}
DATA['blackgc14p']['dc/tex.pak'] = '/root/probe/lanes-20261014/t11/data/tex-t11.pak'
CLASH = [('blackps2', 'r10bcut'), ('blackps2', 'smx103'), ('blackgc', 'r10bcut'), ('blackgc', 'smx103'), ('blackps2', 'blackgc'),
         ('blackgc14', 'blackgc'), ('blackgc14', 'blackps2'), ('blackgc14', 'r10bcut'), ('blackgc14', 'smx103'),
         ('blackgc14p', 'leonhr'), ('blackgc14p', 'blackgc14'), ('blackgc14p', 'blackgc')]
# Leon light (lane lp2, d44c3059): LEON_LIGHT_HEADROOM=1 needs Leon's 15 atlas / hair / pl08 packages at 2x in tex.pak
# (cb_headroom.py over the test 10 GC-atlas pak; same keys, sizes, formats; sha256 1eb18ec4...). Without it Leon draws
# at half brightness; never stage it with a knob-off binary (2x bright).
DATA['leonhr'] = {'dc/tex.pak': '/root/probe/lanes-20261014/lp2/hr/tex-gcatlas-hr.pak'}
# VRAM reclaim (lane vram12, 2026-10-14; data only, render only; tools/d367/vram/vq_pak.py over tex-t11.pak):
#   blackgc14v  = blackgc14p with r101's 12 large 16-bit PS2 world textures (ARGB4444, >= 16 KiB) as full-codebook VQ,
#                 same keys / sizes / formats / material names: 458,752 -> 81,920 B of VRAM (sha256 b7d7622b)
#   blackgc14vl = blackgc14v plus Leon's atlas ec255e66-76812316 as VQ (524,288 -> 67,584 B; LVQ, needs the user's
#                 look decision; sha256 fb12d131)
DATA['blackgc14v'] = dict(DATA['blackgc14p'], **{'dc/tex.pak': '/root/probe/lanes-20261014/vram12/data/tex-vr12-ps2vq.pak'})
DATA['blackgc14vl'] = dict(DATA['blackgc14p'], **{'dc/tex.pak': '/root/probe/lanes-20261014/vram12/data/tex-vr12-both.pak'})
CLASH += [(v, o) for v in ('blackgc14v', 'blackgc14vl') for o in ('blackgc14p', 'blackgc14', 'blackgc', 'blackps2', 'leonhr',
                                                                   'blackgc14v' if v == 'blackgc14vl' else 'blackgc14vl')]
T11_DATA = 'r119c,em29,fbec,r100tr4,smx101,blackgc14p'  # test 11 recipe: GC bake (no r119) + Leon 2x, both in tex.pak
# sg101 (lane objs 10-15): PS2_STRIP_GROUPS=1 data for r101 = ps2lib/world/r101-sg4 (tools/ps2_strip_groups.py --groups 4
# of the test 11 r101 package f5592282: same size, strips re-ordered into spatial groups, every meshlet draws the same
# triangles (sgcheck.py) + ps2-world.r4sg group records, mesh crc checked at open). Harmless with the knob off.
DATA['sg101'] = {'dc/native/r101/ps2-world.%s' % x: PRIV + '/ps2lib/world/r101-sg4/ps2-world.%s' % x for x in ('re4mesh', 'r4sg')}
# PS2 room objects (lane objs, docs/lanes/objs.md; Phase 2 B1 extended, test 12 candidate, NOT in T11_DATA): room
# archives st1/rNNN.dar whose room-code set pieces and etc models (boxes, barrels, doors, racks, ladders, ...) carry
# the PS2 geometry (tools/ps2_objects.py room --keep-larger; r101 BIN 0x20 = the burning stake is world-owned: the PS2
# draws it in its scenario SMD, so the GC copy is emptied). Disc data only; the executable is unchanged.
# objs-<room> = one room (unpadded payload), objs = every room below, objs-r100p / objs-r101p = payload padded to the
# source size (equalised heap 4 arms). r119 keeps r119c (look lane: et1100 + BIN 0x22 together make the dark block).
OBJS_ROOMS = 'r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r117 r118 r11a r11b'.split()
OBJS = PRIV + '/objs-20261014'
# objs-<room>: the shared PS2 library copy (re4-assets-private/ps2lib/objects/<room>/<room>.dar; INDEX.tsv rows, gate
# per object); byte-identical to the lane's objs-20261014/<room>o dars.
PS2LIB = PRIV + '/ps2lib/objects'
for _r in OBJS_ROOMS:
    DATA['objs-' + _r] = {'st1/%s.dar' % _r: '%s/%s/%s.dar' % (PS2LIB, _r, _r)}
DATA['objs'] = {k: v for _r in OBJS_ROOMS for k, v in DATA['objs-' + _r].items()}
# objs12: the rooms whose library rows passed the test 12 gates (r100: H2 STRICT 4702 + s30 340/340; r101: warp STRICT
# 2402 + LEON-GC + TEX_CHECK); the other rooms are test 13 (coordinator 10-14: the all-room objects pass is test 13).
DATA['objs12'] = {k: v for _r in ('r100', 'r101') for k, v in DATA['objs-' + _r].items()}
# objs12b (lane objs cca4f2bf, 10-15, coordinator: the breakable class stays GameCube): objs12 with every cEmBox /
# cEmBarrel etc model left GC (EtcModel.cpp SetBox / SetBarrel: et0100 et0200 et1100 et1200 et1e00 et1f00 et2d00
# et2e00/01 et2f00/01 et3c00). Their break (debris effects owned by the box model) is where et1100's PS2 geometry went
# wrong. r100b: et0100 et0200 GC; r101b: et0100 et0200 et1100 et1e00 GC. Every other object as objs12. (Only these data
# set lines are taken from cca4f2bf; its --uv-fold option and test 14 study sets stay on lane/objs.)
DATA['objs-r100b'] = {'st1/r100.dar': OBJS + '/r100b/r100.dar'}
DATA['objs-r101b'] = {'st1/r101.dar': OBJS + '/r101b/r101.dar'}
DATA['objs12b'] = {**DATA['objs-r100b'], **DATA['objs-r101b']}
# test 13, not ready (tex13/NOT-READY.txt): r11a + et1000 torch from r109's PS2 ETM (--etm-from), and the PS2-picture
# object dars (tools/ps2_objects_tex.py; colour-only swap: flag-4 mask pairs missing until the items lane pair logic).
DATA['objs-r11a2'] = {'st1/r11a.dar': OBJS + '/r11ao2/r11a.dar'}
TEX13 = OBJS + '/tex13'
for _r in OBJS_ROOMS:
    DATA['objst-' + _r] = {'st1/%s.dar' % _r: '%s/%s/%s.dar' % (TEX13, _r, _r), 'tex': '%s/%s/tex' % (TEX13, _r)}
for _r in ('r100', 'r101'):
    DATA['objs-%sp' % _r] = {'st1/%s.dar' % _r: '%s/%sp/%s.dar' % (OBJS, _r, _r)}
# (later --data names win: '--data <test 11 data>,objs,objs-r100p' = every room with the padded r100)
# Test 12 (rc dry run round 2, 2026-10-15; t12/rc-dry, test12/t12-build.sh T12REC; rebuild: test12/t12-texpak.sh):
#   t12tex    = blackgc14p with tex.pak = tex_merge.py of tex-t11.pak (1582e5c5) + fx12 tex-t11-ps2lib.pak (653e622b,
#               PS2 effect library, FX_PS2_PACK / PAL4) + vram12 tex-vr12-both.pak (blackgc14vl: r101 world VQ + Leon's
#               atlas ec255e66-76812316 as VQ, user decision 10-14 23:58 "Leon ships VQ") + the merchant's 4 texture
#               keys (packed, not loose: test 11's loose-texture lesson), then tex_wrapsafe.py (TEX_WRAP_SAFE)
#               + (vram12 D5) dc/resident.bin: the per-room first-sight texture lists (ROOM_RESIDENT=1), built by
#               t12-texpak.sh from vram/resident/r*.tsv
#   objs12    = lane objs' r100 + r101 PS2 room objects from ps2lib/objects (r101 = 32dfe338); accepted for test 12
#               (coordinator 10-15)
#   sg101     = PS2_STRIP_GROUPS=1 r101 world package (ps2lib/world/r101-sg4, built from the r101 package f5592282 =
#               smx101's ps2-world.re4mesh); it comes after smx101 in T12_DATA so it replaces that mesh. If smx101 ever
#               changes, regenerate it (tools/ps2_strip_groups.py + worldlean/sgcheck.py): the runtime refuses a stale r4sg
#   merchant  = ps2lib/cast/r102/merchant-em18 (PS2_CAST_MERCHANT=1): registry + em18.drs (its textures are in t12tex)
T12D = os.environ.get('T12D', '/root/probe/lanes-20261014/t12rc/data')   # T12D=<dir>: a lane's own tex-t12b.pak + resident.bin
DATA['t12tex'] = dict(DATA['blackgc14p'], **{'dc/tex.pak': T12D + '/tex-t12d.pak', 'dc/resident.bin': T12D + '/resident.bin'})
MERCHANT = PRIV + '/ps2lib/cast/r102/merchant-em18'
DATA['merchant'] = {k: MERCHANT + '/' + k for k in ('dc/native/r102/registry.re4nmr', 'em/em18.drs')}
CLASH += [('t12tex', o) for o in ('blackgc14p', 'blackgc14', 'blackgc', 'blackps2', 'leonhr', 'blackgc14v', 'blackgc14vl')]
# PS2 Ganado accessories (test 12 item, lane ps2cast 2026-10-15; tools/d367/ps2cast/ps2_accessories.py): the village
# Ganados' cObj12 caps / hats / glasses (em15 ARC 0x25F..0x269, em10SetAccesory) with the PS2 geometry and the PS2
# pictures (8 dc/tex packages, loose here; a release puts them in tex.pak). em15.drs keeps its size and every other
# byte outside ARC 0x25F..0x268 (the span is re-laid out in place; 2 NTR rows rebased). Disc data only; NOT in T11_DATA.
DATA['acc12'] = {'em/em15.drs': PRIV + '/ps2lib/cast/common/acc12/em15.drs',
                 'tex': PRIV + '/ps2lib/cast/common/acc12/tex'}
# acc12all: the same conversion in every Ganado archive that carries these entries (byte-identical GC and PS2 entries):
# em12 (r100, r11a), em13 (r104), em15 (r101), em17 (r108; no ARC 0x262..0x264).
DATA['acc12all'] = dict(DATA['acc12'], **{'em/%s.drs' % n: PRIV + '/ps2lib/cast/common/acc12/%s.drs' % n
                                          for n in ('em12', 'em13', 'em17')})
CLASH += [('acc12', 'acc12all')]
# PS2 pickups / debris (lane items, docs/lanes/items.md; test 12 candidate, NOT in T11_DATA). tools/ps2_items.py pack
# writes the PS2 item models (ITM), the breakable debris models (Efm in the room EFF and the ETM .eff members) and their
# PS2 pictures over the GC bytes in place (payload size unchanged), on top of lane objs' dars (objs-20261014/<room>o;
# r119: r119c). items-<room> therefore replaces objs-<room> (and r119c). 'items' = every route room + core.das (core
# EFF debris) + the 18 SS/cmn pick-up zoom models + tex-items.pak (tex-t11.pak + the 71 PS2 item / debris packages).
# Pair the arm with EFM_PS2_CUT=1 to stop drawing the debris models the PS2 deleted. Disc data only.
ITEMS_ROOMS = 'r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r117 r118 r119 r11a r11b'.split()
ITEMS = PRIV + '/items-20261014'
for _r in ITEMS_ROOMS:
    DATA['items-' + _r] = {'st1/%s.dar' % _r: '%s/%si/%s.dar' % (ITEMS, _r, _r)}
DATA['items'] = {k: v for _r in ITEMS_ROOMS for k, v in DATA['items-' + _r].items()}
DATA['items']['etc/core.das'] = ITEMS + '/core/core.das'
DATA['items']['dc/tex.pak'] = ITEMS + '/tex-items.pak'
for _f in sorted(Path(ITEMS + '/sscmn').glob('itm*')) if Path(ITEMS + '/sscmn').is_dir() else []:
    DATA['items']['ss/cmn/' + _f.name] = str(_f)
CLASH += [('items', 'leonhr')]
# Test 12 round 3 (rc dry run, 2026-10-15): items + acc12 join the stack.
#   t12tex  now = tex-t12c.pak: t12-texpak.sh also merges lane items' tex-items.pak (86 PS2 pickup / debris packages)
#           and acc12's 8 accessory packages (packed, not loose); sha256 1d52762d
#   items12 = lane items' data on the RC's dars: r100 / r101 / r119 = the lane's dars (packed on objs12 / r119c, the same
#           inputs as the RC); the other 14 route rooms = ps2_items.py pack (ps2_items-v2 lib) re-run on the RC's own
#           dars (p2b-20261011 objects / audio-overlay; objs for those rooms is test 13), same asset names and results
#           per room as the lane, NTR verify OK; core.das = the lane's (pack-core on the RC's core.das gives the same
#           439ba106); the 18 SS/cmn pick-up zoom models. No tex.pak here (it is in t12tex). Recipe knob EFM_PS2_CUT=1.
#   acc12d  = acc12all without the loose 'tex' (its 8 packages are in t12tex)
T12I = T12D + '/items'
DATA['items12'] = {k: v for _r in ('r100', 'r101', 'r119') for k, v in DATA['items-' + _r].items()}
# Release candidate (10-15): r100 / r101 items repacked on the objs12b dars (ps2_items.py pack, lane items lib; the same
# run on the objs12 dars reproduces the lane's e28f4c55 / 298daec6; same asset results: r100 17 ps2, r101 29 ps2 + 1 NONE):
# r100 4abfcc88 (on objs r100b c0eced0b), r101 f77af17a (on objs r101b fbb12e34).
for _r in ('r100', 'r101'):
    DATA['items12']['st1/%s.dar' % _r] = '%s/%sb/%s.dar' % (T12I, _r, _r)
for _r in ('r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r117 r118 r11a r11b').split():
    DATA['items12']['st1/%s.dar' % _r] = '%s/%s/%s.dar' % (T12I, _r, _r)
DATA['items12'].update({k: v for k, v in DATA['items'].items() if k == 'etc/core.das' or k.startswith('ss/cmn/')})
DATA['acc12d'] = {k: v for k, v in DATA['acc12all'].items() if k != 'tex'}
CLASH += [('items12', 'items'), ('acc12d', 'acc12'), ('acc12d', 'acc12all')]
# order matters: items12 after objs12 / r119c (its dars replace theirs), acc12d last
T12_DATA = 'r119c,em29,fbec,r100tr4,smx101,sg101,t12tex,objs12b,merchant,items12,acc12d'
NAME = re.compile(r'^([0-9a-f]{8})-([0-9a-f]{8})\.re4tex$')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]


def texdir(d, r, rec):
    n = 0
    for p in sorted(Path(d).rglob('*.re4tex')):
        if NAME.match(p.name.lower()):
            k = 'dc/tex/%s/%s' % (p.name[0].lower(), p.name.lower())
            if k in r and r[k] != str(p) and sha(r[k]) != sha(str(p)):
                raise SystemExit('texture %s staged twice with different bytes: %s / %s' % (k, r[k], p))
            r[k] = str(p); n += 1
    rec.append('texdir %s %d' % (d, n))


def main():
    a = sys.argv[1:]
    new, out = a[:2]
    pairs = list(zip(a[2::2], a[3::2]))
    opt = {}
    for k, v in pairs:
        opt.setdefault(k, []).append(v)
    base = opt.get('--base', [BASE])[0]
    old = opt.get('--base-label', [BASE_LABEL])[0]
    d = json.load(open(base))
    s = json.dumps(d).replace('candidate-route' + old + '/', 'candidate-route' + new + '/')
    d = json.loads(s)
    r = d['replace']
    rm = set(d.get('remove', []))
    rec = []
    names = [x for v in opt.get('--data', []) for x in v.split(',') if x]
    for a_, b_ in CLASH:
        assert not (a_ in names and b_ in names), 'data sets %s and %s replace the same files' % (a_, b_)
    for nm in names:
        for k, v in DATA[nm].items():
            if k == 'tex':
                for t in (v if isinstance(v, list) else [v]):
                    texdir(t, r, rec)
                continue
            assert os.path.exists(v), (nm, k, v)
            r[k] = v; rm.discard(k); rec.append('%s %s %s' % (nm, k, sha(v)))
    for kv in opt.get('--set', []):
        k, v = kv.split('=', 1)
        assert os.path.exists(v), v
        r[k] = v; rm.discard(k); rec.append('set %s %s' % (k, sha(v)))
    for k in opt.get('--rm', []):
        r.pop(k, None); rm.add(k); rec.append('rm ' + k)
    for t in opt.get('--texdir', []):
        texdir(t, r, rec)
    for k, f in (('--warp', 'dc/warp.txt'), ('--pad', 'dc/padscript.txt'), ('--qtxt', 'dc/quality.txt')):
        if k in opt:
            r[f] = opt[k][0]
            rm.discard(f)
    d['remove'] = sorted(rm)
    d.setdefault('provenance', {})['t11'] = {'base': base, 'label': [old, new], 'data': names, 'staged': rec,
                                             'opts': {k: v for k, v in opt.items()}}
    left = [k for k, v in r.items() if isinstance(v, str) and 'candidate-route' in v and 'candidate-route' + new + '/' not in v]
    assert not left, left
    json.dump(d, open(out, 'w'), indent=1, sort_keys=True)
    print('fixture', out, 'data', ','.join(names) or '-', 'staged', len(rec), 'warp', r.get('dc/warp.txt'),
          'pad', r.get('dc/padscript.txt'))


if __name__ == '__main__':
    main()
