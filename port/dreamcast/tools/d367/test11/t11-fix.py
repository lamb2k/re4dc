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
# Payload root (lane payroot18, 2026-10-18): the 10-17 /root wipe removed BASE and most data-set sources. One payload root,
# extracted from the live release disc (fp_iso.py extract; tree/ = every disc file but 1ST_READ.BIN, MANIFEST-disc.json),
# replaces them: --base payload (or a missing BASE) builds the base fixture from it. It already carries the release's
# data sets (16.4 = T16_DATA), so release-equivalent fixtures pass no --data; a named set whose source is gone still fails.
PAYLOAD_ROOT = os.environ.get('RE4DC_PAYLOAD_ROOT', '/root/re4payload/t164-20261018')
HARNESS = os.environ.get('RE4DC_HARNESS', '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/'
                         'continuation-20260927/playability-r11-r1')
STAGE_BASE = os.environ.get('RE4DC_STAGE_BASE', '/root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7')


def payload_base(label):
    """Base fixture from the payload root: every payload file whose sha256 differs from the stager's base disc
    (STAGE_BASE/payload-manifest.json; all files when it is unreadable), the label's route overlays from the harness
    program dir (candidate-route<label>/, as older fixtures staged them), no 1ST_READ.BIN (the stager adds the arm's)."""
    man = json.load(open(os.path.join(PAYLOAD_ROOT, 'MANIFEST-disc.json')))
    try:
        sb = json.load(open(os.path.join(STAGE_BASE, 'payload-manifest.json')))
    except (OSError, ValueError):
        sb = {}
    sb_sha = {v['sha256'] for v in sb.values()}
    r, kept, renamed = {}, 0, []
    prog = os.path.join(HARNESS, 'programs', 'candidate-route' + label)
    for k, v in sorted(man.items()):
        if k == '1ST_READ.BIN':
            continue
        if k.endswith('.ovl') and k.startswith('dc/') and os.path.exists(os.path.join(prog, k[3:])):
            r[k] = os.path.join(prog, k[3:])
            continue
        if k in sb and sb[k]['sha256'] == v['sha256']:
            kept += 1
            continue
        if k not in sb and not k.isascii() and v['sha256'] in sb_sha:
            renamed.append(k)  # the Shift-JIS item list name: same bytes on the base under its decoded name
            continue
        src = os.path.join(PAYLOAD_ROOT, 'tree', k)
        assert os.path.isfile(src) and os.path.getsize(src) == v['size'], src
        r[k] = src
    # rel17b (10-18): every route overlay of the arm under test, also those the payload's release did not have (Test 17's
    # STAGE_OVL stage overlays st1_0..st2_0: without them the disc halts "route overlay missing on the disc").
    if os.path.isdir(prog):
        for o_ in sorted(os.listdir(prog)):
            if o_.endswith('.ovl') and 'dc/' + o_ not in r:
                r['dc/' + o_] = os.path.join(prog, o_)
    rm = sorted(x for x in sb if x not in man and x.isascii())
    return dict(replace=r, remove=rm, provenance=dict(payload=dict(root=PAYLOAD_ROOT, stage_base=STAGE_BASE, label=label,
                same_as_base=kept, staged=len(r), non_ascii_same_bytes=len(renamed))))
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
AFTER = []
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
# v3pak: crowd12 STACK v3 tex.pak (tex_merge.py of tex-t11.pak + fx12 ps2lib + vram12 world VQ, wrap-safe marked)
DATA['v3pak'] = {'dc/tex.pak': '/root/probe/lanes-20261014/crowd12/data/tex-v3-ws.pak'}
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
# objs12n (10-15): objs12 with r101's ETM et1100 (wood box) left GameCube: the game builds the box's break debris from
# the model's own triangles (GC 164 incl. 24 inward splinter faces; PS2 68, all outward), so the PS2 box drew a flat
# dark shard where GC draws white splinters (r119 et1100-only run r119e-m). objs-20261014/r101n = ps2_objects.py room
# with the r101o arguments minus et1100.bin; every other object identical.
DATA['objs-r101n'] = {'st1/r101.dar': OBJS + '/r101n/r101.dar'}
DATA['objs12n'] = {**DATA['objs-r100'], **DATA['objs-r101n']}
# objs12b (10-15, coordinator: the breakable class stays GameCube): objs12 with every cEmBox / cEmBarrel etc model left
# GC (EtcModel.cpp SetBox / SetBarrel: et0100 et0200 et1100 et1200 et1e00 et1f00 et2d00 et2e00/01 et2f00/01 et3c00).
# Their break (debris effects owned by the box model) is where et1100's PS2 geometry went wrong. r100b: et0100 et0200 GC;
# r101b: et0100 et0200 et1100 et1e00 GC. Every other object as objs12.
DATA['objs-r100b'] = {'st1/r100.dar': OBJS + '/r100b/r100.dar'}
DATA['objs-r101b'] = {'st1/r101.dar': OBJS + '/r101b/r101.dar'}
DATA['objs12b'] = {**DATA['objs-r100b'], **DATA['objs-r101b']}
# test 14 (complete-world objects): r11a + et1000 torch from r109's PS2 ETM (--etm-from), and objst-<room> = PS2 geometry +
# PS2 pictures with material pairs (tools/ps2_objects_tex.py v2: flag-4 parts get a pair package keyed (new colour, GC
# mask); the lane items 421b7251 rules) in re4-assets-private/objs-20261014/tex14 (tex13 = colour-only, superseded).
# objst-r11a carries the r11a2 geometry (+ et1000).
# r119 dark block study (test 14): the p2b 10-11 package with BIN 0x22 (tree) AND ETM et1100 (box) converted (look lane:
# the block shows only with both; r119c = BIN 0x22 only is in T11_DATA).
DATA['r119-both'] = {'st1/r119.dar': PRIV + '/p2b-20261011/objects/r119b/r119.dar'}
# objst-r119 (test 14): BIN 0x22 (tree) + ETM et1100 (box) PS2 geometry (p2b r119b) with their PS2 pictures (tex14/r119).
# The look lane's dark block = a flat dark shard drawn by the PS2 et1100 fragment where GC draws white splinters; it
# is the same with these PS2 pictures (r119t-m), so not the picture (open: fragment UVs / normals / colour). Logic is
# identical (t119-c vs t119-b / t119-t STRICT 902 ticks MUST-IDENTICAL).
DATA['objst-r119'] = {'st1/r119.dar': OBJS + '/tex14/r119/r119.dar', 'tex': OBJS + '/tex14/r119/tex'}
# objsf-r119 (converter v3, --uv-fold): BIN 0x22 + et1000 + et1100 PS2 geometry with each PS2 triangle's UVs folded into
# [0, 1] (the GC models' range; the game clamps et11.eff's box picture, so the PS2 box UVs u -0.96..-0.02 drew one
# edge texel = the dark block) + PS2 pictures (tex15/r119).
DATA['objsf-r119'] = {'st1/r119.dar': OBJS + '/tex15/r119/r119.dar', 'tex': OBJS + '/tex15/r119/tex'}
# r119-box (study): only ETM et1100 (wood box) PS2 geometry, GC pictures (work/out/r119e; not a library asset)
DATA['r119-box'] = {'st1/r119.dar': '/root/probe/lanes-20261014/objs/work/out/r119e/r119.dar'}
DATA['objs-r11a2'] = {'st1/r11a.dar': OBJS + '/r11ao2/r11a.dar'}
TEX14 = OBJS + '/tex14'
for _r in OBJS_ROOMS:
    DATA['objst-' + _r] = {'st1/%s.dar' % _r: '%s/%s/%s.dar' % (TEX14, _r, _r), 'tex': '%s/%s/tex' % (TEX14, _r)}
# objs13-<room> / objs13 (lane objs 10-15, test 13, on the published test 12 package pkg-t12c2tP.json): PS2 room objects
# for r102..r10b, r117, r118, r119, r11a, r11b with the breakable class left GameCube (gen13.sh: ps2_objects.py from the
# GC source dars, so the p2b PS2 breakables of tests 8..12 go back to GC), lane items' ps2_items.py pack on top (same
# changed bytes / counts as the test 12 items dars) and PS2 pictures (ps2_objects_tex.py v2, --pak tex-t12d.pak).
# Replaces the test 12 st1/<room>.dar of items12 / the RC's items dars; r100 / r101 stay objs12b + items (test 12).
# Gates: docs/lanes/objs.md "Test 13 objects on the test 12 base". Use with the test 12 base: t11-fix.py <label> <out>
# --base .../t12rc/fix/pkg-t12c2tP.json --base-label t12c2tP --data objs13.
OBJS13 = OBJS + '/t13'
OBJS13_ROOMS = 'r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r117 r118 r119 r11a r11b'.split()
for _r in OBJS13_ROOMS:
    DATA['objs13-' + _r] = {'st1/%s.dar' % _r: '%s/%s/%s.dar' % (OBJS13, _r, _r), 'tex': '%s/%s/tex' % (OBJS13, _r)}
DATA['objs13'] = {'st1/%s.dar' % _r: '%s/%s/%s.dar' % (OBJS13, _r, _r) for _r in OBJS13_ROOMS}
DATA['objs13']['tex'] = OBJS13 + '/tex-all'  # one copy per key (store13.sh; shared pictures differ only in header source name)
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
# Test 12.1 (lane t12dark, 2026-10-15; T12-DARK-ROOMS-20261015.md): the GC light bake (blackgc) darkened rooms that
# test 10 drew lit (r11b lake shore dock: planks and ground near-black on the console and in Flycast). 12.1 swaps the 14
# baked rooms to the PS2 formula (blackps2: --a0-light ps2, black faces 0..2.5% per room, t11-bk.md) with the same
# program and recipe as test 12. r119 keeps the test 10 package, as in test 12 (heap 4 / El Gigante movies).
#   blackps2w = blackps2 without r119 and without its loose newtex (the 295 re-keyed textures go into tex.pak)
#   t121tex   = tex.pak = test12/t12-texpak.sh with BLACK=blackps2/newtex (tex-t12d.pak + 293 new keys, no key changed;
#               sha256 b097d061); resident.bin unchanged (r101 only)
DATA['blackps2w'] = {k: v for k, v in DATA['blackps2'].items() if k != 'tex' and not k.startswith('dc/native/r119/')}
T121D = os.environ.get('T121D', '/root/probe/t12dark/data')
DATA['t121tex'] = {'dc/tex.pak': T121D + '/tex-t121.pak'}
T121_DATA = T12_DATA + ',blackps2w,t121tex'  # order: after t12tex (its blackgc meshes and tex.pak are replaced)
# Test 13 (t13/rc, 2026-10-15; TEST13-SCOPE.md, test13/t13-build.sh T13REC; rebuild the pak: test13/t13-texpak.sh):
#   objs13d  = objs13 (lane objs e19e146e, v5) without its loose pictures: the 15 room dars r102..r11b, r117..r11b (breakables
#              back to GameCube: the "dark box debris" fix); their 32 pictures are in t13tex
#   ashley13 = PS2_ASHLEY=2 + PS2_ASHLEY_ROOMS=1 (lane ps2cast3 d940cbc0, user choice B): r117's package (registry.re4nmr,
#              no room package there), r118's second package (partner.re4nmr beside the room's own registry.re4nmr) and the
#              texture-prepared em/pl11.drs (596b29aa); her 4 pictures are in t13tex. The other Ashley rooms (r111 r112 r113
#              r11c r11f) are chapter 2-2 / 2-3, not on this disc.
#   bake13   = STATIC_OBJ_BAKE=1 (lane crowd12-t13 ce0b7a82): the r101 world package with the 14 baked objects appended
#              (re4-assets-private/crowd12-bake-20261015/r101-t13, built on smx101 f5592282 + strip groups); replaces sg101
#   t13tex   = dc/tex.pak = tex_merge.py over tex-t12d.pak of tex-t121.pak (12.1, b097d061), tex-t13o.pak (lane objs,
#              06e18e13: tex-t12d + the 32 objs13 pictures) and Ashley's 4 pictures (texpack.py)
OBJS13D = {k: v for k, v in DATA['objs13'].items() if k != 'tex'}
DATA['objs13d'] = OBJS13D
ASHLEY = PRIV + '/ps2lib/cast'
DATA['ashley13'] = {'dc/native/r117/registry.re4nmr': ASHLEY + '/r117/ashley-pl11/dc/native/r117/registry.re4nmr',
                    'dc/native/r118/partner.re4nmr': ASHLEY + '/r118/ashley-pl11/dc/native/r118/partner.re4nmr',
                    'em/pl11.drs': ASHLEY + '/r117/ashley-pl11/em/pl11.drs'}
BAKE13 = PRIV + '/crowd12-bake-20261015/r101-t13'
DATA['bake13'] = {'dc/native/r101/ps2-world.%s' % x: '%s/ps2-world.%s' % (BAKE13, x) for x in ('re4mesh', 'r4pw', 'r4sg', 'ids')}
T13D = os.environ.get('T13D', '/root/probe/lanes-20261015/t13rc/data')
# RC round 3 (10-15): tex-t13v.pak = tex-t13.pak (2ba86e68) + Ashley's 9 pl11 pictures as VQ (test13/vq16-ashley13.txt;
# r117 entry preload refused an effect picture with them 16-bit). t13-texpak.sh builds both.
DATA['t13tex'] = {'dc/tex.pak': T13D + '/tex-t13v.pak'}
CLASH += [('objs13d', 'objs13'), ('t13tex', 'leonhr')]
# order: objs13d after items12 (its dars replace the test 12 ones), bake13 after sg101 / smx101, t13tex after t121tex
T13_DATA = T121_DATA + ',objs13d,ashley13,bake13,t13tex'
# Test 14 #1 (VRAM rule gap, 10-15): r101's resident list made complete (vram_gate strict: 0 uploads after the room-entry
# preload at the r101 cross and the r101 entry; 12.2 had 24). res14 = dc/resident.bin = vram/resident_keys.py pack of
# vram/resident/r*.tsv: r101 152 -> 190 keys (+18 PS2 item and 9 breakable pictures of test 12's items12 / objs12b, the
# r100/common effect pictures r101 draws, 7 PS2 world keys; ~210 KB VRAM), sub screen (radio call) loads left out.
# r000.tsv = the core set (4 HUD pictures, CORE_PIN=1). sha256 1196b77d41d7d0e1.
T14D = os.environ.get('T14D', '/root/probe/lanes-20261015/squeeze/rel14')
DATA['res14'] = {'dc/resident.bin': T14D + '/resident.bin'}
# Test 14 r103 (10-15): res14r3 = res14 + vram/resident/r103.tsv (52 keys, 491,052 B VRAM: the farm view and the r101
# door entry; 47-51 first-sight uploads per 45 s of farm play before, 0 after). 246 records, sha256 8a307ffc3770058a.
T14R3D = os.environ.get('T14R3D', '/root/probe/lanes-20261015/squeeze/rel14r3')
DATA['res14r3'] = {'dc/resident.bin': T14R3D + '/resident.bin'}
# Test 14 (t14/rc, 2026-10-15; TEST14-SCOPE.md, test14/t14-build.sh T14REC): test 13's data + res14r3 (replaces T13's
# dc/resident.bin; order: last).
T14_DATA = T13_DATA + ',res14r3'
# Test 15 row 7 (t15/int, 10-15; lane ps2cast14 b00f9a43, PS2CAST-20261014.md "released rooms ch1-1..2-1"): cast15 = the PS2
# small cast room packages (recipe PS2_CAST_CH1=1 PS2_CAST_BOAT=1 ACTOR_PALETTE_BANK=40 NATIVE_MODEL_REGISTRY_POOL=1) and the
# texture-prepared archives em2a em24 em27 em29 em2e pl0f; their pictures are loose here (the candidate merges them into
# tex.pak). r117: the zealot pool package is the room's registry.re4nmr and Ashley's r117 package moves to partner.re4nmr
# (the lane's r117-zp-p gate fixture; PS2_ASHLEY_ROOMS=1 reads it). r118: reg-118pc (em17 pool; its cart rows are unused,
# em3b is not linked). Order: after T14_DATA (replaces ashley13's r117 registry and the earlier r100 / r104 / r118 packages).
C15D = os.environ.get('C15D', '/root/probe/lanes-20261015/ps2cast')
_C15R = {'100': '100', '104': '104', '105': '105', '106': '106', '107': '107', '108': '108', '10a': '10a', '10b': '10b',
         '11a': '11a', '11b': '11b', '117': '117p', '118': '118pc'}
DATA['cast15'] = {'dc/native/r%s/registry.re4nmr' % r: '%s/conv-t14/reg-%s/package/r%s/registry.re4nmr' % (C15D, g, r)
                  for r, g in _C15R.items()}
DATA['cast15']['dc/native/r117/partner.re4nmr'] = ASHLEY + '/r117/ashley-pl11/dc/native/r117/registry.re4nmr'
for _n in ('em2a', 'em24', 'em27', 'em29', 'em2e', 'pl0f'):
    DATA['cast15']['em/%s.drs' % _n] = '%s/prep14/%s/%s.drs' % (C15D, _n, _n)
# reg-118pc/tex holds 0e80c998-3aeeebb9 with other bytes than reg-108 / reg-118 (same size, a re-encode); one key, one
# picture in tex.pak: the reg-108 bytes (ae7e472f) ship, so r118 uses C15T118 = reg-118pc/tex without that file.
C15T118 = os.environ.get('C15T118', '/root/probe/lanes-20261015/t15k/data/reg-118pc-tex')
DATA['cast15']['tex'] = ['%s/conv-t14/reg-%s/tex' % (C15D, g) if g != '118pc' else C15T118 for g in _C15R.values()] + \
    ['%s/prep14/%s' % (C15D, _n) for _n in ('em2a', 'em24', 'em27', 'em29', 'em2e', 'pl0f')]
# Test 15 GANADO_LOD=1 GANADO_LOD_LEVEL=2 (lane leonlod): the Ganado LOD package (glod_pack.py; sha256 46566154). Without it
# on the disc the LOD code never runs (no GANADOLOD log line: the poc101 bench trap).
GLOD = os.environ.get('GLOD', '/root/probe/lanes-20261015/t15k/data/glod/ganado_lod.re4gl')
DATA['glod'] = {'dc/native/ganado/ganado_lod.re4gl': GLOD}
T15_DATA = T14_DATA + ',cast15,glod,res16,snd16,res16h,vq16w,water16i,fsh'  # vq16w + water16i (lane water16b) replace vq16cs + water16h; fsh (lane farshell16) last: the far shells of r100 / r101; res16 after res14r3: the HUD fix core set (CORE_PIN=2); snd16 (lane audio16) after objs13d: replaces st1/r103.dar + bgm/aica_str.dat, needs AICA_STR_ENT_MAX=48; res16h + vq16cs (lane resident16) after res16 / t13tex: chapter 1 resident lists + VQ tex.pak; water16h (lane water16) after res16h: res16h + the WATER_PS2 room water pictures; wv32r101 (world32, ChatGPT) replaces bake13 r101 world files and adds variant 5
# Test 15 HUD fix (t15/hud, CORE_PIN=2): res16 = res14r3 + the two HUD pictures the r101 post-bell radio call's frag window
# released (test 14's open VRAM item): afa4bc82-306be3e3 (44x44) and bf17fc06-c975b3a7 (48x48), in the core set r000.tsv.
# 248 records, sha256 de98da1ec2e75532 (resident_keys.py pack r000 r101 r103).
T15RD = os.environ.get('T15RD', '/root/probe/lanes-20261015/t15k/data/res16')
DATA['res16'] = {'dc/resident.bin': T15RD + '/resident.bin'}  # order: after res14r3
# Test 15 per-room large texture reads (lane plainread16, user-approved 10-16; TEX_PACK_WINDOW): texord16 = t13tex's
# tex-t13v.pak with its packages laid out in the chapter 1 route's preload order (texpak_order.py over the d01..d13 door
# runs; every key byte-identical, index unchanged but offsets). Must come after every set that replaces dc/tex.pak.
TEXORD = os.environ.get('TEXORD', '/root/probe/lanes-20261016/prk/data/texord16')
DATA['texord16'] = {'dc/tex.pak': TEXORD + '/tex.pak'}
# Not in T15_DATA (option A keeps stream reads; the layout moves load timing). Add it after every tex.pak set with TEX_PACK_WINDOW.
# Chapter 1 sound completion (lane audio16, 10-16; data only, no knob, no AICA layout change):
#   st1/r103.dar = objs13d's r103.dar with its ROOM (ambience) and FOOT (footsteps) banks prebuilt into the frozen AICA layout
#     (aica_banks.py fit --room r103: 16000 / 11025 Hz, the preferred caps; arena 1,004,192 = r103's enemies 668,192 + these
#     263,616 + 72,384 left). objs13 had rebuilt r103.dar from an unconverted .dar, so both went to runtime conversion and
#     were silent ("blk 6 / blk 5 does not fit"). Only those two ARAM parts differ from objs13d's file. sha256 see SND16/README.
#   bgm/aica_str.dat = aica_banks.py streams --streams ch1: the ch21r file (entries 0..17 and their bytes unchanged) plus the
#     27 chapter 1 streams that were "not in aica_str.dat, silent" (death screen 0:0, r102 0:25, r104/r107 0:10, r104 0:21,
#     r106 0:7, r108 0:51, r100 0:18 / 1:34, r101 1:62 / 1:59, r104 1:134, r10b 1:29, the merchant's 15 voice lines
#     1:180..1:194). 45 entries, disc +16.6 MB, no AICA or KOS change.
# NEEDS the game knob AICA_STR_ENT_MAX=48 (+512 B .bss): with the default 32 the reader refuses the whole 45-entry file and
# every disc stream (music, radio voices) goes silent. Order: after objs13d (it replaces objs13d's st1/r103.dar).
SND16 = os.environ.get('SND16', PRIV + '/audio16-20261016')
DATA['snd16'] = {'st1/r103.dar': SND16 + '/st1/r103.dar', 'bgm/aica_str.dat': SND16 + '/bgm/aica_str.dat'}
# Lane resident16 (2026-10-16, VRAM rule: a room's textures load once at its entry; user approved the VQ look 10-16:
# "vq looks fine go for it"). Data only, no knob: ROOM_RESIDENT=1 reads dc/resident.bin.
#   res16h = dc/resident.bin with resident lists for every chapter 1 room and r119 (vram/resident/r000 r100 r101 r102 r103
#     r104 r105 r106 r107 r108 r109 r10a r10b r119.tsv; regenerate with: resident_keys.py pack <out> r000.tsv r100.tsv
#     r101.tsv r102.tsv r103.tsv r104.tsv r105.tsv r106.tsv r107.tsv r108.tsv r109.tsv r10a.tsv r10b.tsv r119.tsv),
#     1064 records, sha256 1e3af15308350b8e. Includes the r100 woods / shed walk (+31 keys) and the Ganado kill / blood
#     effect set (16 keys) in r103 r104 r106..r10a r119 (not r105: thrash-guard refusals in the chapter 1-2 segment).
#   vq16cs = dc/tex.pak: tex-t13v.pak (9bbe65e6) with 39 16-bit pictures as full-codebook VQ, made by vram/vq16c-texpak.sh
#     in three passes (vq16-ch1.txt: Leon pl08, PS2 world r102 r105 r108 r10b, em17 cast; vq16-results.txt: the chapter
#     results screen; vq16-r104.txt: em13 / em18 cast), 3,817,472 -> 557,056 B, PSNR 26.8..57.5 dB; sha256 15611245a3ae1a82.
#   Both files live (not in git) in RS16D = /root/probe/lanes-20261015/t15k/data/{res16h,vq16cs}. Order: after res16 and
#   t13tex (they replace dc/resident.bin and dc/tex.pak). The lane's intermediate sets (res16c..g, vq16c, vq16cr) stay in
#   RS16L = /root/probe/lanes-20261016/resident-k/data (evidence C:\Flycast-Evidence\re4-dreamcast\resident-20261016).
RS16D = os.environ.get('RS16D', '/root/probe/lanes-20261015/t15k/data')
RS16L = os.environ.get('RS16L', '/root/probe/lanes-20261016/resident-k/data')
DATA['res16h'] = {'dc/resident.bin': RS16D + '/res16h/resident.bin'}
DATA['vq16cs'] = {'dc/tex.pak': RS16D + '/vq16cs/tex-vq16c.pak'}
# World32 r101: approved L2 look, 32 m opaque static batches; four base files and
# two variant files must travel together because the R4PW tables are shared.
WV32D = os.environ.get('WV32D', PRIV + '/world32-r101-20261016')
DATA['wv32r101'] = {'dc/native/r101/' + _n: WV32D + '/' + _n for _n in (
    'ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids', 'ps2-world.r4sg',
    'ps2-wv5.re4mesh', 'ps2-wv5.r4sg')}
# Test 16 r101 world (lane/worldtest16, user plan 10-16: no structural world cuts): wt16r101 = world32 with the landmarks
# kept at level 0 (stake crossbar + pyre planks via a vertex box, the house fence segments, the well, the low fence); same
# six files and R4PW tables as wv32r101 (replaces it). Since 10-16 evening: set C16 = that set + mesh 0x17 (the house-front
# fence rails, which the per-vertex reduction collapsed) at level 0, re4-assets-private/world-r101-wt16c16-20261016
# (SHA256SUMS, RECIPE.txt); the first set (C4, test 16 until then) stays in world-r101-wt16-20261016 (WT16D overrides).
WT16D = os.environ.get('WT16D', PRIV + '/world-r101-wt16c16-20261016')
DATA['wt16r101'] = {'dc/native/r101/' + _n: WT16D + '/' + _n for _n in (
    'ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids', 'ps2-world.r4sg',
    'ps2-wv5.re4mesh', 'ps2-wv5.r4sg')}
for _n in ('res16c', 'res16d', 'res16e', 'res16f', 'res16g'):
    DATA[_n] = {'dc/resident.bin': RS16L + '/' + _n + '/resident.bin'}
for _n in ('vq16c', 'vq16cr'):
    DATA[_n] = {'dc/tex.pak': RS16L + '/' + _n + '/tex-vq16c.pak'}
# FAR_SHELL (lane farshell16, 2026-10-16; T15REC T15_FS): far-shell.fsh per room (tools/d367/farshell, built from the test 14
# candidate's r101 / r100 PS2 world packages; the world's own texture keys, 0 B of VRAM). fsh6 = the shipped set (user 10-16
# "short shell + half vertices"): params v6, r101 3,200 triangles / 6,634 vertices, r100 2,900 / 7,044 (weld 150 mm,
# border-weighted collapse, integer UV shifts). fsh3 = v3, the first approved look (6000 triangles, 13,457 / 14,177
# vertices). fsh5 (v3 + a coarse level beyond 18.75 m, version 2) priced the same as v3, not used. r10b is never cut by
# the View distance option (kViewRoomMin), so it has no shell. Disc data only; read by FAR_SHELL=1 builds. Private store:
# re4-assets-private/farshell-20261016/<set>/<room>/far-shell.fsh (release kit: Build-Assets).
FSH = os.environ.get('FSH', PRIV + '/farshell-20261016/fsh6')
DATA['fsh'] = {'dc/native/%s/far-shell.fsh' % r: FSH + '/%s/far-shell.fsh' % r for r in ('r100', 'r101')}
DATA['fsh1'] = DATA['fsh']   # the lane's fixture name
# Lane water16 (WATER_PS2=1, test 15, user option A 10-16): water16h = res16h + the WATER_PS2 pictures of the rooms
# drawn (tools/d367/water/resident/r107 r108 r10a r11a .tsv; regenerate with: water_resident.py pack
# $RS16D/res16h/resident.bin <out> r107.tsv r108.tsv r10a.tsv r11a.tsv). Replaces dc/resident.bin: order after res16h.
# 1092 records (1064 + 28), sha256 f043586efa564000. r10b / r11b lists wait in resident/after-room-lists/ (no VRAM
# room). Lives in RS16D/water16h (not in git).
DATA['water16h'] = {'dc/resident.bin': RS16D + '/water16h/resident.bin'}
# water16i (lane water16b, 10-16): res16h + the new r11b list (vram/resident/r11b.tsv, 20 keys) + all six rooms' water
# pictures (water/resident/r107 r108 r10a r10b r11a r11b .tsv; resident_keys.py pack of
# vram/resident/*.tsv, then water_resident.py pack): 1084 + 50 records, sha256 0699533aac59b55d. Replaces water16h.
# vq16w (lane water16b, 10-16): vq16cs + 7 r10b / r11b RGB565 pictures as full-codebook VQ (vram/vq16-lake.txt, Del Lago
# em2f, boat pl0f, PS2 world r10b; PSNR 29.5-52.8 dB; 1,081,344 -> 149,504 B of VRAM), so the lakes' water pictures fit
# the room preloads (user rule 10-16: VQ by default when it frees needed capacity). Replaces vq16cs. sha256 ae84c909afea8f4a.
DATA['water16i'] = {'dc/resident.bin': RS16D + '/water16i/resident.bin'}
DATA['vq16w'] = {'dc/tex.pak': RS16D + '/vq16w/tex-vq16c.pak'}
# Chapters 2-2 / 2-3 (lane ch2code16, 10-16; CH2-CODE-COMPLETE-20261016.md): ch2 = the chapter 2 route data (tools/d367/ch2/
# mkch2data.py: route-v7's 2-2 / 2-3 rooms over test 15's data, r11d / r11e released rooms, em16 prepared, the 53-entry
# chapter 1+2 stream file). Order: last (after T15_DATA). Needs the game's chapter 2 knobs (ch2/ch2-build.sh CH2REC,
# AICA_STR_ENT_MAX >= 53). 'unremove': base-disc pictures the 2-2 / 2-3 rooms read stay on the disc.
# ch2data-20261018 (lane ashley17) = ch2data-20261016 + Ashley's partner packages for r10f / r11d / r11e / r200 (the
# entries mkch2data.py adds; route-v7 and the ch2 lane inputs mkch2data.py reads were lost 10-17, so the 10-16 set was
# copied and the four added; provenance in its ch2-data.json).
CH2D = os.environ.get('CH2D', '/root/re4data/private/ch2data-20261018')
UNREMOVE = {}
if os.path.exists(CH2D + '/ch2-data.json'):
    _c2 = json.load(open(CH2D + '/ch2-data.json'))
    DATA['ch2'] = dict(_c2['replace'])
    # the chapter 2 room overlays (ROUTE_CH22 pl14, ROUTE_CH23 em3b / em35) of the arm under test: the base fixture has
    # no row for them, so its label swap cannot reach them (a missing overlay halts "route overlay missing on the disc")
    DATA['ch2']['ovl'] = ['em3b', 'em35', 'pl14']
    UNREMOVE['ch2'] = _c2['unremove']
# cast16 (lane cast16, 10-16; PS2CAST-20261014.md 2026-10-16 section): PS2 cast packages over ch2 (order: after ch2).
# r11c Luis + merchant13 (reg-11cm), r11d cart + em16 pool (reg-11dp), r11e El Gigante + its g70 gameplay level
# (reg-11eL), r11f Mendez g70 in every form (reg-11fLo; user 10-16: the cutscenes are movies) + the PS2 Ashley partner,
# with their textures. Needs NATIVE_MODEL_REGISTRY_FIRST=1 NATIVE_MODEL_REGISTRY_LOD=1 (ch2/ch2-build.sh CH2REC) and
# PRIM_BUF_KB (T15_PB): r11f's heap 4 holds Ashley's 239,688 B cell only with the primitive buffer at 432 KB.
C16D = os.environ.get('C16D', '/root/re4data/private/cast16data-20261016')
if os.path.exists(C16D + '/cast16-data.json'):
    DATA['cast16'] = dict(json.load(open(C16D + '/cast16-data.json'))['replace'])
# Boss18 I-005 (10-18): explicit Test18-only El Gigante g50 gameplay data.
# CH2REC already enables FIRST/LOD; the existing selector retains full for events/grabs.
# Never add this to T15_DATA/T17_DATA. ch2/ch2-gigante-g50.sh applies it explicitly.
B18G50D = os.environ.get('B18G50D', '/root/re4data/private/boss18-gigante-g50-t18-20261018')
DATA['boss18g50'] = {'dc/native/r119/registry.re4nmr': B18G50D + '/native/r119/registry.re4nmr',
                     'dc/native/r11e/registry.re4nmr': B18G50D + '/native/r11e/registry.re4nmr',
                     'tex': B18G50D + '/tex'}
# Disc 1 texture packing (lane pak17, 10-16; coordinator round 4 "loose -> pack", test 17): pak17 = dc/tex.pak holding
# every loose texture of the test 17 disc (T15_DATA + ch2 + cast16 over the package base tree), built by
# tools/d367/vram/disc_pack.py over ch2's tex.pak (13340bfa, 21:54 data): the 1,250 loose keys the pack already held
# are dropped (the pack is looked up first, so they were never read), 241 opaque 16-bit pictures >= 16 KiB re-encoded
# as full-codebook VQ (PSNR >= 29 dB; UI, alpha and small pictures stay 16-bit), the other 1,075 moved in as they are.
# tex.pak 4,904 -> 6,220 keys, 119,822,336 -> 144,570,368 B (sha256 52d9b0013315c5e9); loose dc/tex 2,566 files /
# 95,596,544 B -> 0; disc tree 1,064.0 -> 997.9 MB.
# DROP_LOOSE: with the set staged, every loose dc/tex/<c>/<key>.re4tex of the fixture and every disc path listed in the
# set's loose-keys.txt (the package base tree's files) is removed from the disc; each must be in the final dc/tex.pak
# (checked here: a loose key the pack lacks stops the fixture). Staleness (base.json): the pack the earlier sets stage
# and every loose texture they stage must be the bytes pak17 was built from; when ch2 / cast16 (or any earlier set)
# changes its pictures, the fixture stops: rebuild pak17 with disc_pack.py --fixture <the fixture without pak17>.
# Order: after every set that stages loose textures or replaces dc/tex.pak (last). Lives in PAK17D (not in git;
# release kit: Build-Assets disc set pak17).
# CAST-GC r108 (lane castgc17, 10-17): r108's registry package with the em17 type 0xc POOL descriptor ganado-em17-0cp
# (model-registry/ps2-ch1-r108p.json; NATIVE_MODEL_REGISTRY_POOL, in T15REC) instead of the non-pool ganado-em17-0c.
# r108 spawns em17 0xc holding a weapon (grip hand 0x1c8): the non-pool rows refused it (NMRU roles) and the GameCube
# model drew on every pass. Its 4 textures are already in pak17's tex.pak (r113p / r118p), so no loose texture.
# Data defaults (release lane rel17b, 10-18): the sets recovered after the 10-17 wipe (lane data17,
# TEST17-DATA-20261018.md; C: twins re4-assets-private/<set>-20261018 with SHA256SUMS): r108p, pak17, zr17, zr17b, v101,
# res17g. The old -20261016 / -20261017 dirs are gone.
R108PD = os.environ.get('R108PD', '/root/re4data/private/r108p-20261018')
DATA['r108p'] = {'dc/native/r108/registry.re4nmr': R108PD + '/registry.re4nmr'}
# CAST-GC r111 (lane notdrawn20, 10-20, GitHub #42): r111's package with the same em17 type 0xc POOL descriptor
# (model-registry/ps2-ch2-r111p.json = ps2-ch2-r113p re-roomed to 111) instead of the non-pool ganado-em17-0c. r111's
# torch / weapon em17 did not bind the non-pool rows: the PS2 Ganado cast declined it and the GameCube model drew (NMRS
# r111 id=17 plan=G declined 746 of 950 passes; with r111p plan=R native 746, declined 0). Its 3 textures are r113p's,
# already in pak17's tex.pak (no loose texture). Heap 4 after the r111 package opens: 7,126,016 free (was 7,199,776).
# Private data /root/re4data/private/r111p-20261020 (C: twin re4-assets-private/r111p-20261020, cast dir inside).
R111PD = os.environ.get('R111PD', '/root/re4data/private/r111p-20261020')
DATA['r111p'] = {'dc/native/r111/registry.re4nmr': R111PD + '/registry.re4nmr'}
# GC purge (lane purge-cast24, 10-24): trap24 = the r111 / r113 registry packages + the PS2 bear traps trap-em2a-00 /
# trap-em2a-02 (model-registry/ps2-ch2-r111t.json / ps2-ch2-r113t.json; descriptors as ps2-ch1-r105). Without a trap
# descriptor the em2a traps drew the GameCube model on the source path (castgc/notdrawn-allow.tsv rows, now dropped).
# Data only, no knob. Order: after ch2 and r111p (it replaces both packages). Atlases b8d5b0e6-ef7ef3c0 /
# 716538d1-87b872c9 are already in the release tex.pak (no loose texture). 90,304 -> 115,456 B per package.
# Private data /root/re4data/private/trap24-20261024 (RECIPE.txt, SHA256SUMS.txt; C: twin re4-assets-private/trap24-20261024).
TRAP24D = os.environ.get('TRAP24D', '/root/re4data/private/trap24-20261024')
DATA['trap24'] = {'dc/native/%s/registry.re4nmr' % _r: '%s/dc/native/%s/registry.re4nmr' % (TRAP24D, _r)
                  for _r in ('r111', 'r113')}
# lane stump17 (10-17): ACTOR_GANADO_PS2_STUMP's variant package (the exact PS2 lost-head stumps of the five cast
# appearances and hand poses 449 / 450 / 454 / 455; tools/d367/ps2_ganado_stump.py). Only with the knob on; no texture.
STUMP17D = os.environ.get('STUMP17D', '/root/re4data/private/stump17-20261017')
DATA['stump17'] = {'dc/native/ganado/ganado_var.re4gv': STUMP17D + '/ganado_var.re4gv'}
# grip24 (lane purge-cast24 10-24, GC purge): stump17's package + the PS2 grip hands 451 / 456 (ps2_ganado_stump.py --grip).
# Only with ACTOR_GANADO_PS2_GRIP=1 ACTOR_GANADO_PS2_STUMP_DIR=<GRIP24D> (the runtime header must match the package).
# Order: after stump17 (it replaces the package). Private store /root/re4data/private/grip24-20261024 (RECIPE.txt).
GRIP24D = os.environ.get('GRIP24D', '/root/re4data/private/grip24-20261024')
DATA['grip24'] = {'dc/native/ganado/ganado_var.re4gv': GRIP24D + '/dc/native/ganado/ganado_var.re4gv'}
PAK17D = os.environ.get('PAK17D', '/root/re4data/private/pak17-20261018')
DATA['pak17'] = {'dc/tex.pak': PAK17D + '/tex.pak'}
# pak17-20261018: tex.pak is verified (52d9b001); loose-keys.txt and base.json were regenerated (no recorded sha) and
# sit in regen/ until promoted. The drop-loose staleness check below is what accepts them.
_PAK17L = PAK17D + '/loose-keys.txt'
DROP_LOOSE = {'pak17': _PAK17L if os.path.exists(_PAK17L) else PAK17D + '/regen/loose-keys.txt'}
LOOSE = re.compile(r'^dc/tex/[0-9a-f]/([0-9a-f]{8})-([0-9a-f]{8})\.re4tex$')


def pak_keys(path):
    import struct
    with open(path, 'rb') as f:
        h = f.read(2048)
        magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', h, 0)
        assert magic == b'RE4PAK1\0' and ver == 1, path
        f.seek(ioff)
        ix = f.read(16 * count)
    return {struct.unpack_from('<2I', ix, 16 * i) for i in range(count)}


# The Flycast stager (playability-r11-r1 stage_scenario.py) always stages the MEDIA overlay (movies and 33 loose textures,
# all in pak17) and refuses a fixture that removes one of its files. A scenario fixture (--warp: never a package) keeps
# those paths off 'remove'; they stay loose on Flycast discs, where the pack still wins (texpack::find comes first).
MEDIA_OVERLAY = os.environ.get('MEDIA_OVERLAY', '/mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads')


def media_paths():
    if not os.path.isdir(MEDIA_OVERLAY):
        return set()
    return {os.path.relpath(os.path.join(d, f), MEDIA_OVERLAY).replace(os.sep, '/')
            for d, _, fs in os.walk(MEDIA_OVERLAY) for f in fs}


PREV_PAK = {}   # data set -> the dc/tex.pak staged before it (drop_loose staleness check)


def drop_loose(names, r, rm, rec):
    lists = [DROP_LOOSE[n] for n in names if n in DROP_LOOSE]
    if not lists:
        return
    pak = r.get('dc/tex.pak')
    assert pak, 'drop-loose: no dc/tex.pak staged'
    have = pak_keys(pak)
    paths = {k for k in r if LOOSE.match(k)}
    for f in lists:
        paths |= {l.strip() for l in open(f) if l.strip()}
    # staleness: pak17 was built from one input pack and one set of loose bytes (base.json); another set staging a
    # newer pack or other loose bytes means the pack holds old pictures (rebuild it: tools/d367/vram/disc_pack.py)
    for n in names:
        if n not in DROP_LOOSE:
            continue
        bj = os.path.join(os.path.dirname(DROP_LOOSE[n]), 'base.json')
        b = json.load(open(bj))
        prev = PREV_PAK.get(n)
        full = lambda p_: hashlib.sha256(open(p_, 'rb').read()).hexdigest()
        if prev is None or full(prev) != b['pak']:
            raise SystemExit('drop-loose: %s was built from another dc/tex.pak than the sets before it stage (%s): '
                             'rebuild it (tools/d367/vram/disc_pack.py)' % (n, prev))
        stale = [k for k in paths if k in r and k in b['loose'] and full(r[k]) != b['loose'][k]]
        new = [k for k in paths if k in r and k not in b['loose']]
        if stale or new:
            raise SystemExit('drop-loose: %s is stale: %d loose textures changed, %d new since it was built (first %s): '
                             'rebuild it (tools/d367/vram/disc_pack.py)' % (n, len(stale), len(new), (stale + new)[:3]))
        # PAK_DERIVED (lane vram101 10-17): a later set may stage a pack made from this one with some packages
        # re-encoded (same keys; its sidecar JSON names the base pack's and its own sha256).
        # Derived packs chain (lane ch2rooms20 10-20: ch21r's pack derives from v101's): follow base -> out links.
        ok = {b['out']}
        derived = [json.load(open(PAK_DERIVED[m_])) for m_ in names if m_ in PAK_DERIVED]
        while True:
            more = {d_['out'] for d_ in derived if d_['base'] in ok} - ok
            if not more:
                break
            ok |= more
        if full(pak) not in ok:
            raise SystemExit('drop-loose: the staged dc/tex.pak is not %s\'s pack (or a pack derived from it)' % n)
    lacking = []
    for k in sorted(paths):
        m = LOOSE.match(k)
        assert m, 'drop-loose: not a loose texture path: ' + k
        if (int(m.group(1), 16), int(m.group(2), 16)) not in have:
            lacking.append(k)
        r.pop(k, None); rm.add(k)
    if lacking:
        raise SystemExit('drop-loose: %d loose textures are not in %s (first %s): rebuild the pack (vram/disc_pack.py)'
                         % (len(lacking), pak, lacking[:3]))
    rec.append('drop-loose %d loose textures (all in %s %s)' % (len(paths), pak, sha(pak)))


# Test 17 data line (the chapter 2 recipe ch2/ch2-build.sh CH2REC over T15REC): T15_DATA + ch2 + cast16, then pak17 last
# (its pack replaces ch2's dc/tex.pak and every loose texture leaves the disc).
# r108p (castgc17 10-17): the CAST-GC r108 em17 fix, before pak17 (stages no texture).
T17_DATA = T15_DATA + ',ch2,cast16,r108p,pak17'
# Lane zeroread17 (coordinator 10-17, "zero disc reads in the r101 fight at cap 6 and in r103"; data only, no knob):
#   em/em15.drs, em/em12.drs = the acc12 archives with their motion hot flags set to the clips the r101 / r103 fights use
#     (tools/d367/motion/motion_flags.py set, lists motion/hot/em15-r101.txt 20 clips 242,176 B and em12-r103.txt 11 clips
#     130,336 B). Before: 79 / 75 clips (991,488 / 952,768 B) flagged hot under the 262,144 B MOTION_PRESSURE_BYTES cap, so
#     each room entry read ~1 MB of keys and evicted 3/4 of them again, and the fight's clips then missed (cold reads).
#   dc/resident.bin = the ch2 method (resident_keys.py pack of vram/resident/*.tsv, then water_resident.py pack) with
#     r101.tsv / r103.tsv extended by the fights' first-sight keys (resident_keys.py list of the lane's runs).
#   Only the flag words and table CRCs change in the archives (same clip payloads, same sizes): residency, not logic.
ZR17D = os.environ.get('ZR17D', '/root/re4data/private/zr17-20261018')
DATA['zr17'] = {'em/em15.drs': ZR17D + '/em15.drs', 'em/em12.drs': ZR17D + '/em12.drs', 'dc/resident.bin': ZR17D + '/resident.bin'}
# zr17-20261018 (recovered 10-18) has only em15.drs: its em12.drs (zr17b's replaces it) and resident.bin (v101's /
# res17g's replace it) were lost and never reach a T17V_DATA disc. Stage only the files the set has.
DATA['zr17'] = {k: v for k, v in DATA['zr17'].items() if k == 'em/em15.drs' or os.path.exists(v)}
T17Z_DATA = T17_DATA + ',zr17'   # zr17 last: it replaces acc12's em15 / em12 and ch2's resident.bin

# lane zeroread17b (2026-10-17): em13 (r104), em17 (r108 / r118) and em12 (r100 + r103 + r11a, shared) motion hot flags =
# the clips those rooms use in play (MOTION_USAGE_LOG + all-cold probe runs; motion/hot/em13-r104.txt,
# em17-r108-r118.txt, em12-r100-r103-r11a.txt; tools/d367/motion/motion_flags.py: MTC flags + table CRC only).
ZR17BD = os.environ.get('ZR17BD', '/root/re4data/private/zr17b-20261018')
DATA['zr17b'] = {'em/em13.drs': ZR17BD + '/em13.drs', 'em/em17.drs': ZR17BD + '/em17.drs', 'em/em12.drs': ZR17BD + '/em12.drs'}
T17ZB_DATA = T17Z_DATA + ',zr17b'   # zr17b last: it replaces acc12 em13 / em17 and zr17 em12
# Lane vram101 (10-17, data only; merged in land/t17-zr17v): v101 = dc/resident.bin packed from every list of this tree
# (vram/resident_keys.py pack vram/resident/*.tsv, then water/water_resident.py pack ... water/resident/*.tsv; 3991
# records, sha256 77a7853ef743a557; r101.tsv carries 076e860e, r101's last first-sight picture) + dc/tex.pak = pak17 with
# the 8 r101 16-bit pictures that reach >= 29 dB as full-codebook VQ (vram/vq17-r101.txt, 40,960 B less VRAM; coordinator
# 10-17). Goes with VRAM_PAGES_VQ_ONLY=1 (T15_VP in T15REC). Rebuild resident.bin when a list changes.
V101D = os.environ.get('V101D', '/root/re4data/private/v101-20261018')
DATA['v101'] = {'dc/resident.bin': V101D + '/resident.bin', 'dc/tex.pak': V101D + '/tex.pak'}
PAK_DERIVED = {'v101': V101D + '/pak-derived.json'}   # v101's tex.pak = pak17 + 8 VQ packages (drop_loose)
# Lane gatlas17 (10-17, data only): res17g = dc/resident.bin packed again from every list of this tree (vram/resident_keys.py
# pack vram/resident/*.tsv, then water/water_resident.py pack ... water/resident/*.tsv; 3,996 records, sha256
# 5cd0e26a2a6c8cde) after r108.tsv gained 6c08f204 (the r108p em17 PS2 atlas, 512x512) and r118.tsv a9d62b83 / 8a4b3f56 /
# 31db8ccd / d425c598 (64x48): the pictures those rooms loaded in play (GATLAS17-20261017.md). Last: replaces v101's.
RES17GD = os.environ.get('RES17GD', '/root/re4data/private/res17g-20261018')
DATA['res17g'] = {'dc/resident.bin': RES17GD + '/resident.bin'}
T17V_DATA = T17ZB_DATA + ',v101,stump17,res17g'   # test 17 data: zr17 + zr17b + v101 (tex.pak) + res17g (resident.bin, last)
# Lane trans17 / release lane rel17 (10-18, user "With trans17"): trans17 = TRANS_POLICY's sidecars (tools/d367/tr_classify.py
# over the PS2 worlds Test 17 ships): dc/native/rXXX/ps2-world.r4tc per classified room (bound to that room's R4PW crc; a
# mismatched pair draws today's path) and the disc index dc/native/trclass.idx (R4TI: only rooms that passed the look gate;
# a room left out of the index draws as today). Stages no texture and no world file. Only with T15_TR (TRANS_POLICY) on.
# T17T_DATA = T17V_DATA + trans17; every other line is unchanged.
TRANS17D = os.environ.get('TRANS17D', '/root/re4data/private/trans17-20261018')
DATA['trans17'] = {'dc/native/trclass.idx': TRANS17D + '/trclass.idx'}
if os.path.isdir(TRANS17D):
    for _r in sorted(os.listdir(TRANS17D)):
        if re.match(r'^r[0-9a-f]{3}$', _r) and os.path.exists('%s/%s/ps2-world.r4tc' % (TRANS17D, _r)):
            DATA['trans17']['dc/native/%s/ps2-world.r4tc' % _r] = '%s/%s/ps2-world.r4tc' % (TRANS17D, _r)
T17T_DATA = T17V_DATA + ',trans17'
# Release lane rel17b (10-18): res17b = dc/resident.bin packed from every list of lane/rel17b (the res17g method): res17g
# + r11b d0f964ff (16.5's res165 key, LAKE_NIGHT_FX's torch flame) + the island lists r300..r333 that t15/int carries
# (RE4DC_RESIDENT_STRICT=1 refused res17g for them); 5,368 records, sha256 98c23bc3. Last: replaces res17g's.
# The Test 17 release line T17R_DATA; release fixtures stage it over the payload base (--base payload --data T17R_PAYLOAD).
RES17BD = os.environ.get('RES17BD', '/root/re4data/private/res17b-20261018')
DATA['res17b'] = {'dc/resident.bin': RES17BD + '/resident.bin'}
T17R_DATA = T17T_DATA + ',res17b'
# Lane fix18 (10-18, Test 18 items 2 and 4; data only, no knob): res18f = dc/resident.bin packed by the res17b method from
# lane/fix18's lists, which add the Test 17 first-sight pictures of r102 (+14, the save-load effect pictures, #33), r100
# (+14, the house fight: 3 Ganado atlases + effects) and r11b (+10, the night lake shore). Strict superset of res17b
# (a9dca43b; only those three rooms differ). Goes last, after res17b, on the Test 18 data line (not T17R_DATA).
RES18FD = os.environ.get('RES18FD', '/root/re4data/private/fix18-20261018')
DATA['res18f'] = {'dc/resident.bin': RES18FD + '/resident.bin'}
# Lane residentbin22 (10-22, data only, no knob): res22 = dc/resident.bin from vram/resident_keys.py release (all
# top-level vram/resident/r*.tsv + water/resident/r*.tsv in one step; the res17b / res18f method, which it rebuilds byte
# for byte: vram/test_resident_release.py). res18f + r100 3d9d333a (in play after the sub screen closes) + 95 census
# in-play uploads of 13 rooms; 5,502 records, sha256 8fb526cc (= vram/resident/RELEASE.sha256). Last: replaces res18f's.
RES22D = os.environ.get('RES22D', '/root/re4data/private/res22-20261022')
DATA['res22'] = {'dc/resident.bin': RES22D + '/resident.bin'}
# Lane codex22 (10-22, Codex audit unit, data only, no knob): lake22 = the lake trees' bark fix (Codex issue52-visuals
# a8bd34686, repair_lake_bark.py): PS2 image 2 (bark) is GC image 4, so 406 bark triangles drew under the alpha-masked
# branch material and the trees looked fragmented. st1/r10b.dar 39bd07e1 -> 8c84649b (same 5,808,128 B; 5,079 bytes of
# BIN 0x1e change; all 529 PS2 triangles kept). Input = the release disc's r10b.dar (checked on cand-d3733810).
LAKE22D = os.environ.get('LAKE22D', '/root/re4data/private/lake22-20261022')
DATA['lake22'] = {'st1/r10b.dar': LAKE22D + '/r10b.dar'}
# Lane inv23 (10-22, user-approved option A): sslz23 = ss/eng/ss_cmmn.lz + ss_pzzl.lz, the sub screen data files packed
# by tools/d367/inv23/ss_lz.py set (one LZ4 block each; 1,443,744 -> 822,053 B; SHA256SUMS in the set). Read only by
# SS_DATA_LZ=1 programs; the .dat files stay on the disc for every other program. Any place in the data line.
SSLZ23D = os.environ.get('SSLZ23D', '/root/re4data/private/sslz23-20261022')
DATA['sslz23'] = {'ss/eng/ss_cmmn.lz': SSLZ23D + '/ss/eng/ss_cmmn.lz', 'ss/eng/ss_pzzl.lz': SSLZ23D + '/ss/eng/ss_pzzl.lz'}
# Lane pvs23 (10-23, Codex visibility23 91640233, data only, no knob): sg109 = r109's strip-group metadata
# (dc/native/r109/ps2-world.r4sg, 76,128 B, sha256 f605d3ca; ps2_strip_groups.py --preserve-order). Binds the mip22b r109
# mesh (d2e244fc) and scoped policy 177cae56, so it needs mip22b + WORLD_RECT21 (release line only, not KSETS); any other
# program finds it stale and draws whole meshlets. Opaque transformed vertices -14% at the r109 entry, on-screen unchanged.
SG109D = os.environ.get('SG109D', '/root/re4data/private/r109-stripgroups23-20261022-v1')
DATA['sg109'] = {'dc/native/r109/ps2-world.r4sg': SG109D + '/r109/ps2-world.r4sg'}
# Release lane rel18 (10-19, Test 18 item 10): garr18h = the LEON_HEADLESS v2 archives of data set garr18-head-20261019
# (tools/d367/ps2leon/build_head.py): em/pl00.drs and em/pl08.drs with GC arc 0xC stubbed and the PS2 severed head as
# its payload. Built from the payload disc's pl00 (1fdb5378) / pl08 (f4acbfad); no set on the Test 18 line stages either.
# Only with LEON_HEADLESS=1 (without the knob the stub would draw nothing for the flying head).
# boss18g50r (rel18, 10-19) = boss18g50's two registries without its tex/ (the Test 18 disc line): on the pak17 line the
# pack is looked up first and already holds both g50 atlases (a383881d with the same bytes as pak17's loose base,
# cd6162c8 a key of its input pack), so the loose copies are never read; drop-loose refuses them as "new" and the
# Build-Assets zip takes no loose textures. This is the data fix18 gated (mkg50.sh: registries only).
DATA['boss18g50r'] = {k: v for k, v in DATA['boss18g50'].items() if k != 'tex'}
G18HD = os.environ.get('G18HD', '/root/re4data/private/garr18-head-20261019')
DATA['garr18h'] = {'em/pl00.drs': G18HD + '/pl00.drs', 'em/pl08.drs': G18HD + '/pl08.drs'}
# pmleon24 (lane purge-motion24 10-24, GC asset purge, data only): garr18h's pl00 / pl08 with Leon's FCV/SEQ motion from the
# PS2 BIO4DAT.AFS pl00.dat / pl08.dat (tools/d367/motion/ps2_motion.py leon): 84 members already PS2-identical, 5 replaced
# in place (FCV 23 empty, SEQ 59 last key 1 frame earlier, FCV 87 / 101 / 117 PS2 re-keyed); offsets and all other bytes
# kept. After garr18h. Gates: bell-trg / door103 / shoot101 trace pairs STRICT, Leon run + aim stills pixel-identical.
# Private store copy: re4-assets-private/pmleon24-20261024.
PMLEON24D = os.environ.get('PMLEON24D', '/root/re4data/private/pmleon24-20261024')
if os.path.isdir(PMLEON24D):
    DATA['pmleon24'] = {'em/pl00.drs': PMLEON24D + '/em/pl00.drs', 'em/pl08.drs': PMLEON24D + '/em/pl08.drs'}
# pmleon24b (same lane, 10-24): REPLACES pmleon24, which edited the unread copy of the original body at 0x400; garr18h's
# live body is the type-0 record at 0x21cde0, so pmleon24 changed no byte the game reads (hence its STRICT gates).
# tools/d367/motion/ps2_motion_prepared.py rewrite + verify on garr18h's pl00 / pl08: the live body's FCV 23 / 87 / 101 /
# 117 and SEQ 59 take the PS2 bytes. Use pmleon24b instead of pmleon24 (after garr18h). Store: re4-assets-private/pmleon24b-20261024.
PMLEON24BD = os.environ.get('PMLEON24BD', '/root/re4data/private/pmleon24b-20261024')
if os.path.isdir(PMLEON24BD):
    DATA['pmleon24b'] = {'em/pl00.drs': PMLEON24BD + '/em/pl00.drs', 'em/pl08.drs': PMLEON24BD + '/em/pl08.drs'}
    CLASH += [('pmleon24', 'pmleon24b')]
# pmgan24 (lane purge-motion24 10-24, GC asset purge, data only): the chapter 1-2 Ganado archives (em12 em15 em13 em17
# em11 em16, the release's prepared zr17 / zr17b / ch2 copies) with their FCV motion from PS2 BIO4DAT.AFS emNN.dat
# (tools/d367/motion/ps2_motion_prepared.py rewrite + verify: bodies laid out again, MTC rebuilt with the PS2 key
# identities, hot sets kept per slot), the 169 PS2 dc/mot keys they stream, and the 169 GC keys no archive references
# any more taken off the disc (remove.txt). SEQ tables were already PS2-identical. After every set that stages those
# archives (zr17, zr17b, ch2): last in the data line. Private store copy: re4-assets-private/pmgan24-20261024.
PMGAN24D = os.environ.get('PMGAN24D', '/root/re4data/private/pmgan24-20261024')
if os.path.isdir(PMGAN24D):
    DATA['pmgan24'] = {'em/%s.drs' % _e: '%s/em/%s.drs' % (PMGAN24D, _e) for _e in ('em12', 'em15', 'em13', 'em17', 'em11', 'em16')}
    DATA['pmgan24'].update({'dc/mot/' + _k: '%s/dc/mot/%s' % (PMGAN24D, _k) for _k in sorted(os.listdir(PMGAN24D + '/dc/mot'))})
    DATA['pmgan24']['remove'] = [_l.strip() for _l in open(PMGAN24D + '/remove.txt') if _l.strip()]
# Lane engine19 (10-19; ENGINE_PREVIEW, the enemy logic engine): rc19 = one room data file per room,
# dc/native/<room>/room.r4rc (tools/enginebake/room_compile.py, R4RC v1 GRID + OCCL v2 wall-check occluders; MANIFEST.tsv
# beside them). Read only by an ENGINE_PREVIEW=1 or ENEMY_VIS_CULL program; knob-off programs never open it. Private store
# copy: re4-assets-private/rc19o2-20261019 (70 rooms r1xx/r2xx; the GRID-only set rc19-20261019 is superseded).
RC19D = os.environ.get('RC19D', '/root/re4data/private/rc19o2-20261019')
if os.path.isdir(RC19D):
    DATA['rc19'] = {'dc/native/%s/room.r4rc' % r: '%s/%s/room.r4rc' % (RC19D, r)
                    for r in sorted(os.listdir(RC19D)) if os.path.isfile('%s/%s/room.r4rc' % (RC19D, r))}
# Lane ch2rooms20 (10-20; ROUTE_CH21_FULL, chapter 2-1's real path): ch21r = rooms r10c (the dam: the insignia key's own
# pickup) / r10d / r10e: st1 arc + dar (GC disc 1, island18 prepare recipe; dar sound banks refitted, r10c's FOOT bank
# tail-first), PS2 worlds + MAINSCENARIO under dc/native/<room>, r102's merchant registry retargeted to r10d / r10e, and
# dc/tex.pak = v101's pack + the rooms' 234 new keys (ch2rooms/pack_add.py; pak-derived.json: base v101's pack). Last in
# the data line. Private store copy: re4-assets-private/ch21r-20261020 (RECIPE.txt, SHA256SUMS).
CH21RD = os.environ.get('CH21RD', '/root/re4data/private/ch21r-20261020')
DATA['ch21r'] = {'dc/tex.pak': CH21RD + '/dc/tex.pak'}
for _r in ('r10c', 'r10d', 'r10e'):
    DATA['ch21r'].update({'st1/%s.%s' % (_r, _x): '%s/st1/%s.%s' % (CH21RD, _r, _x) for _x in ('arc', 'dar')})
    for _f in ('ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids', 'registry.re4nmr'):
        if _f != 'registry.re4nmr' or _r != 'r10c':
            DATA['ch21r']['dc/native/%s/%s' % (_r, _f)] = '%s/dc/native/%s/%s' % (CH21RD, _r, _f)
PAK_DERIVED['ch21r'] = CH21RD + '/pak-derived.json'
# nostd20 (lane ch2rooms20 10-20, disc space: Test 20 was 4,401 sectors over the GD-ROM high-density zone with ch21r):
# removes the GC scenery package dc/native/<room>/MAINSCENARIO.re4mesh of every route room that has a PS2 world. With
# PS2_WORLD_ROOMS=2 (the recipe) native_static.cpp no_std_skip never opens it in a room whose PS2 world preloads
# ("native mesh: no-std room=...: scenery package not opened"). r100 (multi-part FILE_0x scenery) and r101 (low/ quality
# packages) keep theirs. A 'remove' entry takes the paths off the disc. Knob-off / PS2_WORLD_ROOMS<2 discs must not stage it.
DATA['nostd20'] = {'remove': ['dc/native/%s/MAINSCENARIO.re4mesh' % _r for _r in (
    'r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r10f r111 r112 r113 r117 r118 r119 r11a r11b '
    'r11c r11d r11e').split()]}
# pair20 (lane release-test20 10-20): the r200 GC material pair a38b935e-3c0af8b7 (colour 3822d4ec-70fde01b + mask
# 9c93897d-8518d3d3), drawn in r200 after the chapter 2-3 truck when LOGIC_LOD_EM=2 shifts the timing; it was never on a
# disc (ch23end texchk FAIL). dc/tex.pak = ch21r's pack + that key (ch2rooms/pack_add.py); last in the data line.
# Private store copy: re4-assets-private/pair20-20261020 (RECIPE.txt, SHA256SUMS).
PAIR20D = os.environ.get('PAIR20D', '/root/re4data/private/pair20-20261020')
DATA['pair20'] = {'dc/tex.pak': PAIR20D + '/dc/tex.pak'}
PAK_DERIVED['pair20'] = PAIR20D + '/pak-derived.json'
# ch21l (lane fix-dam-light 10-20, GitHub #47): r10c / r10d / r10e PS2 worlds reconverted with the PS2 amb_scr measured
# in PCSX2 (cLightEnv bytes 0..2 over PINE at each door arrival: r10c 50,45,40; r10d 14,23,38; r10e 45,45,45) instead of
# ch21r's GC LIT cut-0 ambient. Supersedes ch21r's ps2-world.* only. The worlds' texture gains move with the light, so
# dc/tex.pak = pair20's pack + 46 new keys (pack_add.py). Last in the data line (after pair20).
# Private store copy: re4-assets-private/ch21l-20261020 (RECIPE.txt, SHA256SUMS).
CH21LD = os.environ.get('CH21LD', '/root/re4data/private/ch21l-20261020')
DATA['ch21l'] = {'dc/tex.pak': CH21LD + '/dc/tex.pak'}
for _r in ('r10c', 'r10d', 'r10e'):
    for _f in ('ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids'):
        DATA['ch21l']['dc/native/%s/%s' % (_r, _f)] = '%s/dc/native/%s/%s' % (CH21LD, _r, _f)
PAK_DERIVED['ch21l'] = CH21LD + '/pak-derived.json'
# sc21 (lane scenery21 10-20, SCENERY_CONE / SCENERY_PIECE_STATE): every PS2 world room's package with facing-grouped
# strip groups (dc/native/<room>/ps2-world.re4mesh + ps2-world.r4sg: the same triangles, corners renumbered per group) and
# its room file with the SCCN / SCPS sections (tools/d367/scenery21/scn21_build.py over the Test 20 line disc's
# dc/native). Last in the data line (after ch21l: built from its r10c..r10e worlds). Knob-off programs read the r4sg
# (PS2_STRIP_GROUPS) and draw the same triangles. Private store copy: re4-assets-private/sc21-20261020 (SHA256SUMS).
SC21D = os.environ.get('SC21D', '/root/re4data/private/sc21-20261020')
if os.path.isdir(SC21D):
    DATA['sc21'] = {'dc/native/%s/%s' % (r, f): '%s/%s/%s' % (SC21D, r, f)
                    for r in sorted(os.listdir(SC21D)) if os.path.isdir('%s/%s' % (SC21D, r))
                    for f in ('ps2-world.re4mesh', 'ps2-world.r4sg', 'room.r4rc')}
# Over the payload base (the 16.4 disc, payroot18), which already carries T15_DATA except the far shells (fsh: 16.x
# shipped without FAR_SHELL): fsh + every set after T15_DATA.
T17R_PAYLOAD = 'fsh' + T17R_DATA[len(T15_DATA):]
assert T17R_DATA.startswith(T15_DATA + ',')
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


def resident_gate(v, rec):
    """Resident-list coverage (lane r200-17, 10-16): the staged dc/resident.bin must carry every key of every
    tools/d367/vram/resident/r<room>.tsv in this tree. A data set packed from an older tree or a partial list set leaves
    rooms re-reading their pictures from disc in play (the ch4 lane's resident-ch3.bin: r10f / r112 49 / 65 uploads
    after the preload). Build the file with vram/resident_keys.py pack over every list (then water/water_resident.py
    pack) or use data set ch2's. Short lists are printed and recorded in provenance; RE4DC_RESIDENT_STRICT=1 (release
    fixtures) refuses them."""
    import glob, importlib.util as iu_
    here_ = os.path.dirname(os.path.abspath(__file__))
    s_ = iu_.spec_from_file_location('resident_keys', os.path.join(here_, '..', 'vram', 'resident_keys.py'))
    m_ = iu_.module_from_spec(s_); s_.loader.exec_module(m_)
    tsvs = sorted(glob.glob(os.path.join(here_, '..', 'vram', 'resident', 'r*.tsv')))
    # A data set that remaps resident keys (mip22: WORLD_RECT21 scoped keys) ships its table beside the file.
    rm_ = os.path.join(os.path.dirname(v), 'resident-remap.tsv')
    remap_ = m_.load_remap(rm_) if os.path.isfile(rm_) else None
    if remap_:
        rec.append('RESIDENT REMAP %s %d' % (rm_, len(remap_)))
    short = m_.coverage(v, tsvs, remap_)
    for room, n, got in short:
        rec.append('RESIDENT SHORT r%03x %d/%d' % (room, got, n))
        sys.stderr.write('t11-fix: dc/resident.bin %s carries %d of the %d keys r%03x lists\n' % (v, got, n, room))
    assert not (short and os.environ.get('RE4DC_RESIDENT_STRICT') == '1'), 'resident gate: %d short lists' % len(short)


def lostpart_gate(k, v, rec):
    """Required gate (2026-10-16): a reduced world level file dc/native/<room>/ps2-wv*.re4mesh is staged only with a PASS
    stamp of the lost-part check beside it (tools/d367/lostpart/lostpart_gate.sh writes LOSTPART.txt: verdict +
    reduced-sha256). RE4DC_LOSTPART_WAIVE=1 = A/B comparison fixtures only (recorded in provenance; never a release)."""
    if not (k.startswith('dc/native/') and os.path.basename(k).startswith('ps2-wv') and k.endswith('.re4mesh')):
        return
    if os.environ.get('RE4DC_LOSTPART_WAIVE') == '1':
        rec.append('LOSTPART WAIVED %s' % k)
        return
    st = os.path.join(os.path.dirname(v), 'LOSTPART.txt')
    assert os.path.exists(st), 'lost-part gate: %s has no LOSTPART.txt (run tools/d367/lostpart/lostpart_gate.sh)' % v
    t = open(st).read()
    import hashlib
    h = hashlib.sha256(open(v, 'rb').read()).hexdigest()
    first = t.splitlines()[0] if t else ''
    assert ': PASS (' in first, 'lost-part gate: %s FAILED the check (%s)' % (v, first)
    assert ('reduced-sha256 %s' % h) in t, 'lost-part gate: %s changed since its LOSTPART.txt stamp' % v
    rec.append('LOSTPART PASS %s %s' % (k, h[:16]))


def main():
    a = sys.argv[1:]
    new, out = a[:2]
    pairs = list(zip(a[2::2], a[3::2]))
    opt = {}
    for k, v in pairs:
        opt.setdefault(k, []).append(v)
    base = opt.get('--base', [BASE])[0]
    old = opt.get('--base-label', [BASE_LABEL])[0]
    if base == 'payload' or (base == BASE and not os.path.exists(BASE)):
        base, old = 'payload:' + PAYLOAD_ROOT, new
        d = payload_base(new)
    else:
        d = json.load(open(base))
    s = json.dumps(d).replace('candidate-route' + old + '/', 'candidate-route' + new + '/')
    d = json.loads(s)
    r = d['replace']
    rm = set(d.get('remove', []))
    rec = []
    names = [x for v in opt.get('--data', []) for x in v.split(',') if x]
    for a_, b_ in CLASH:
        assert not (a_ in names and b_ in names), 'data sets %s and %s replace the same files' % (a_, b_)
    # AFTER (lane purge-ui24 10-24): (set, needs): set stages only with needs named before it (its pack derives from it).
    for a_, b_ in AFTER:
        if a_ in names:
            assert b_ in names[:names.index(a_)], 'data set %s needs %s before it in --data' % (a_, b_)
    for nm in names:
        rm -= set(UNREMOVE.get(nm, ()))
        for k, v in DATA[nm].items():
            if k == 'ovl':
                prog = os.path.dirname(os.path.dirname(next(x for x in r.values() if isinstance(x, str) and
                                                             'candidate-route' + new + '/' in x)))
                for o_ in v:
                    f_ = '%s/candidate-route%s/%s.ovl' % (prog, new, o_)
                    assert os.path.exists(f_), f_
                    r['dc/%s.ovl' % o_] = f_; rm.discard('dc/%s.ovl' % o_); rec.append('%s ovl %s' % (nm, o_))
                continue
            if k == 'remove':   # paths the set takes off the disc (nostd20)
                for p_ in v:
                    r.pop(p_, None); rm.add(p_); rec.append('%s rm %s' % (nm, p_))
                continue
            if k == 'dc/tex.pak' and nm in DROP_LOOSE:
                PREV_PAK[nm] = r.get('dc/tex.pak')
            if k == 'tex':
                for t in (v if isinstance(v, list) else [v]):
                    texdir(t, r, rec)
                continue
            assert os.path.exists(v), (nm, k, v)
            lostpart_gate(k, v, rec)
            r[k] = v; rm.discard(k); rec.append('%s %s %s' % (nm, k, sha(v)))
    for kv in opt.get('--set', []):
        k, v = kv.split('=', 1)
        assert os.path.exists(v), v
        lostpart_gate(k, v, rec)
        r[k] = v; rm.discard(k); rec.append('set %s %s' % (k, sha(v)))
    for k in opt.get('--rm', []):
        r.pop(k, None); rm.add(k); rec.append('rm ' + k)
    for t in opt.get('--texdir', []):
        texdir(t, r, rec)
    drop_loose(names, r, rm, rec)
    if '--warp' in opt:
        kept = rm & media_paths()
        if kept:
            rm -= kept; rec.append('scenario fixture: %d MEDIA overlay paths kept off remove' % len(kept))
    if 'dc/resident.bin' in r:
        resident_gate(r['dc/resident.bin'], rec)
    rm -= set(r)  # a staged loose picture (data 'tex' dirs, --texdir) wins over the base's removal of the same file
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

# ash21 (lane release-test21 10-20, Test 21 item 7, user "Put her fix in test 21"): Codex qa21-r11e corrected Ashley
# archive em/pl11.drs (QA Alpha Fix 1, tag e974d7b0): ch2's pl11 (ecf30980) with the three cold r11e pre-fight clips kept
# in the admitted body (167 loads/evictions, 3,011 reads over 111 ticks -> none); prebuilt AICA sound preserved.
# After ch2 in the data line. Private store copy: re4-assets-private/ash21-20261020 (RECIPE.txt, SHA256SUMS).
ASH21D = os.environ.get('ASH21D', '/root/re4data/private/ash21-20261020')
DATA['ash21'] = {'em/pl11.drs': ASH21D + '/em/pl11.drs'}

# mip22 (lane mipmap22 10-22, Test 22): the texture pipeline data for CAST_MIPMAP / TEX_*_MIPMAP / WORLD_RECT21: dc/tex.pak
# = pack v5 (a21e75d1: ch21l's pack with 885 packages re-encoded with mip chains and 798 scoped rect21 keys added; every
# base key kept), the 27 PS2 worlds' r4pw part records rekeyed to the scoped keys, and dc/resident.bin remapped to them.
# Last in the data line (after ash21). Release discs only (not in KSETS). Private store copy:
# re4-assets-private/mip22-20261022 (RECIPE.txt, SHA256SUMS).
MIP22D = os.environ.get('MIP22D', '/root/re4data/private/mip22-20261022')
if os.path.isdir(MIP22D):
    DATA['mip22'] = {'dc/tex.pak': MIP22D + '/dc/tex.pak', 'dc/resident.bin': MIP22D + '/dc/resident.bin'}
    for _r in sorted(os.listdir(MIP22D + '/dc/native')):
        DATA['mip22']['dc/native/%s/ps2-world.r4pw' % _r] = '%s/dc/native/%s/ps2-world.r4pw' % (MIP22D, _r)
    PAK_DERIVED['mip22'] = MIP22D + '/pak-derived.json'
# mip22b (lane mipfault22 10-22): mip22 with da197067-8f589a03 held at its ch21l 16-bit original. mip22 had re-encoded it
# to PAL8 and r11c ran out of PAL8 palette blocks (TEXCHK r11c "PVR palette banks exhausted" on 48f71838). Replaces mip22
# in the data line. Private store copy: re4-assets-private/mip22b-20261022 (RECIPE.txt, SHA256SUMS).
MIP22BD = os.environ.get('MIP22BD', '/root/re4data/private/mip22b-20261022')
if os.path.isdir(MIP22BD):
    DATA['mip22b'] = {'dc/tex.pak': MIP22BD + '/dc/tex.pak', 'dc/resident.bin': MIP22BD + '/dc/resident.bin'}
    for _r in sorted(os.listdir(MIP22BD + '/dc/native')):
        DATA['mip22b']['dc/native/%s/ps2-world.r4pw' % _r] = '%s/dc/native/%s/ps2-world.r4pw' % (MIP22BD, _r)
    PAK_DERIVED['mip22b'] = MIP22BD + '/pak-derived.json'
# fol24 (lane mip-finish24 10-24, Test 23): mip22b's tex.pak + coverage-preserving alpha mip chains for 169 held foliage /
# cut-out keys of the 27 ch1-ch2 PS2 worlds (tools/d367/foliagemip22/recover_alpha.py). Needs FOLIAGE_MIP24=1 (86 rebound
# rect21 rows). After mip22b; release line only (not KSETS). Private store copy: re4-assets-private/fol24-20261024.
FOL24D = os.environ.get('FOL24D', '/root/re4data/private/fol24-20261024')
if os.path.isdir(FOL24D):
    DATA['fol24'] = {'dc/tex.pak': FOL24D + '/dc/tex.pak'}
    PAK_DERIVED['fol24'] = FOL24D + '/pak-derived.json'
# props24 (lane purge-props24 10-24, GC purge: set objects): the ch2 rooms' non-breakable etc models and room BINs as PS2
# geometry + PS2 pictures (purge24/gen24.sh = objs13's ps2_objects.py + ps2_objects_tex.py): r10d r10e r10f r111 r112 r113
# r11c r11d r11e r11f r200; offline census GC 54 -> 5 (r10c BIN 0x1f extended weights, r10f et2900 / r11c BIN 0x1f PS2
# placeholders, r113 / r11c et0c00 and r11f et1c00 absent from the PS2 ETM: PS2_ETS_MATCH=2 drops their entries).
# dc/tex.pak = fol24's pack + 16 keys (pack_add.py). After fol24 (its tex.pak). Release line only (fol24 is not in KSETS).
# props24p (after props24): + window panes et0000 / et2500 emptied (the PS2 model is a placeholder) in r100 r101 r105 r107
# r111 r11c r11f and et0001's PS2 picture in r111 r11c r11f (the pane no longer shares it). Store: RECIPE.txt + SHA256SUMS.
PROPS24D = os.environ.get('PROPS24D', '/root/re4data/private/props24-20261024')
if os.path.isdir(PROPS24D):
    DATA['props24'] = {'dc/tex.pak': PROPS24D + '/dc/tex.pak', 'st2/r200.dar': PROPS24D + '/st2/r200.dar'}
    for _r in 'r10d r10e r10f r111 r112 r113 r11c r11d r11e r11f'.split():
        DATA['props24']['st1/%s.dar' % _r] = '%s/st1/%s.dar' % (PROPS24D, _r)
    PAK_DERIVED['props24'] = PROPS24D + '/pak-derived.json'
PROPS24PD = os.environ.get('PROPS24PD', '/root/re4data/private/props24p-20261024')
if os.path.isdir(PROPS24PD):
    DATA['props24p'] = {'dc/tex.pak': PROPS24PD + '/dc/tex.pak'}
    for _r in 'r100 r101 r105 r107 r111 r11c r11f'.split():
        DATA['props24p']['st1/%s.dar' % _r] = '%s/st1/%s.dar' % (PROPS24PD, _r)
    PAK_DERIVED['props24p'] = PROPS24PD + '/pak-derived.json'
# atlas24 (lane purge-props24 10-24, after props24p): r117 BIN 0x1f (the church chandelier) PS2 geometry + one PS2 atlas
# picture (ps2_objects.ATLAS_OBJECTS: GC 256x256 <- PS2 images 0 / 1 / 3 packed 256x128). dc/tex.pak = props24p's + 2 keys.
ATLAS24D = os.environ.get('ATLAS24D', '/root/re4data/private/atlas24-20261024')
if os.path.isdir(ATLAS24D):
    DATA['atlas24'] = {'dc/tex.pak': ATLAS24D + '/dc/tex.pak', 'st1/r117.dar': ATLAS24D + '/st1/r117.dar'}
    PAK_DERIVED['atlas24'] = ATLAS24D + '/pak-derived.json'
# props24b (same lane, after atlas24; r11e.dar breakables class only: the items class cost 131 KB of heap 4 there): the breakable boxes / barrels (et0100 et0200 et1100 et1200 et1e00 et1f00 et2d00
# et2e00/01 et2f00/01 et3c00) PS2 geometry in every ch1-2 room; their picture is the debris effect model's TPL (already PS2
# in ch1 via items12); the ch2 rooms also get the PS2 break debris and pickups (ps2_items.py over a lane lib). 28 st1 room
# files + st2/r200.dar (list: the store's SHA256SUMS). dc/tex.pak = atlas24's + 22 keys.
PROPS24BD = os.environ.get('PROPS24BD', '/root/re4data/private/props24b-20261024')
if os.path.isdir(PROPS24BD):
    DATA['props24b'] = {'dc/tex.pak': PROPS24BD + '/dc/tex.pak', 'st2/r200.dar': PROPS24BD + '/st2/r200.dar'}
    for _f in sorted(os.listdir(PROPS24BD + '/st1')):
        DATA['props24b']['st1/' + _f] = PROPS24BD + '/st1/' + _f
    PAK_DERIVED['props24b'] = PROPS24BD + '/pak-derived.json'
# props24l (same lane, after props24b): leftovers. r105 / r107 et0001 (window frame) picture to PS2 (its pane is emptied by
# props24p), r11e room BIN 0x23 (falling rock) picture to PS2 (EFF#22 efm 0x20). dc/tex.pak = props24b's (keys already held).
PROPS24LD = os.environ.get('PROPS24LD', '/root/re4data/private/props24l-20261024')
if os.path.isdir(PROPS24LD):
    DATA['props24l'] = {'dc/tex.pak': PROPS24LD + '/dc/tex.pak', 'st1/r105.dar': PROPS24LD + '/st1/r105.dar',
                        'st1/r107.dar': PROPS24LD + '/st1/r107.dar', 'st1/r11e.dar': PROPS24LD + '/st1/r11e.dar'}
    PAK_DERIVED['props24l'] = PROPS24LD + '/pak-derived.json'
# props24x (same lane, after props24l): r10c room BIN 0x1f (extended-weights ModelData) to PS2 geometry + picture.
PROPS24XD = os.environ.get('PROPS24XD', '/root/re4data/private/props24x-20261024')
if os.path.isdir(PROPS24XD):
    DATA['props24x'] = {'dc/tex.pak': PROPS24XD + '/dc/tex.pak', 'st1/r10c.dar': PROPS24XD + '/st1/r10c.dar'}
    PAK_DERIVED['props24x'] = PROPS24XD + '/pak-derived.json'
# pui24 (lane purge-ui24 10-24, GC asset purge): fol24's tex.pak with the core HUD pictures as PS2 Core.dat pixels under
# their GC keys (tools/d367/purgeui24/ps2_hud_pak.py; ammo lens, life sphere, gauge arcs / domes, name label, bullet,
# partner icons, Ashley gauge, d-pad, the two UI_HUD_MASK composites): 14 packages, same sizes and formats. Data only, no
# knob. After fol24; release line only (not KSETS). Private store copy: re4-assets-private/pui24-20261024.
PUI24D = os.environ.get('PUI24D', '/root/re4data/private/pui24-20261024')
if os.path.isdir(PUI24D):
    DATA['pui24'] = {'dc/tex.pak': PUI24D + '/dc/tex.pak'}
    PAK_DERIVED['pui24'] = PUI24D + '/pak-derived.json'
# pfx24 (lane purge-fx24 10-24, GC asset purge): pui24's tex.pak with the r117 church candle flames (GC EFF 0x86, 16 x
# 64x128 frames) as the PS2 r10e.dat EFF #7 0x86 flipbook (same 16 frames and size; PS2 r117.dat has no 0x86), PAL4
# under the GC keys (tools/d367/purge-fx24/fx_cross_room.py pack). Data only; pair with FX_PS2_NONE_CUT=1 (its table no
# longer cuts these keys in r117). After pui24. Private store copy: re4-assets-private/pfx24-20261024.
PFX24D = os.environ.get('PFX24D', '/root/re4data/private/pfx24-20261024')
if os.path.isdir(PFX24D):
    DATA['pfx24'] = {'dc/tex.pak': PFX24D + '/dc/tex.pak'}
    PAK_DERIVED['pfx24'] = PFX24D + '/pak-derived.json'
# pui24s (lane purge-ui24 10-24, GC purge: sub screen + etc pictures): pfx24's tex.pak (chain fol24 -> pui24 -> pfx24 ->
# pui24s, rebuilt 10-24 on pfx24 7a54e971) + 880 pictures of ss/Item ss/Cmn
# ss/Eng, etc/*.tpl, etc/memcard.das and op/*.das as their PS2 twins' pictures under the GC keys (purgeui24/ps2_tpl_pak.py,
# NCC-matched; same sizes and formats). Needs pfx24 before it (AFTER); pui24 and pfx24 stay in the line. Store: re4-assets-private/
# pui24s-20261024 (on pfx24; the pui24-based pack eba16350 is retired).
PUI24SD = os.environ.get('PUI24SD', '/root/re4data/private/pui24s-20261024')
if os.path.isdir(PUI24SD):
    DATA['pui24s'] = {'dc/tex.pak': PUI24SD + '/dc/tex.pak'}
    PAK_DERIVED['pui24s'] = PUI24SD + '/pak-derived.json'
    AFTER += [('pui24s', 'pfx24'), ('pfx24', 'pui24')]
# pui24f (lane purge-ui24 10-24, GC purge: fonts): the English glyph sheets as PS2 glyphs. The PS2 USA build's only Latin
# font is common_p.fnt, cell for cell the GC common_p layout (+ PS2 pad glyph rows the Dreamcast does not use), so
# common_p.fnt and the per-stage *_p sheets (stage1/2, event1-3, sscrn) get the PS2 cells and width bytes in the GC
# container (tools/d367/purgeui24/ps2_font.py; same sizes; le_mirror form, pipeline identity checked). No runtime change.
# Independent of the tex.pak sets. Store: re4-assets-private/pui24f-20261024 (RECIPE.txt + SHA256SUMS + report.json).
PUI24FD = os.environ.get('PUI24FD', '/root/re4data/private/pui24f-20261024')
if os.path.isdir(PUI24FD):
    DATA['pui24f'] = {'font/' + _n: PUI24FD + '/font/' + _n for _n in sorted(os.listdir(PUI24FD + '/font'))}
# leonhair24 (lane purge-cast24 10-24, GC purge; data only, no knob): fol24's tex.pak with Leon's hair from the PS2 disc
# (pl08.dat TPL 3 image 0, transposed to the GC layout) under the GC keys: pairs fc24a99c / 9cf7f055 (what the hair
# materials draw; graded per channel to the shipping pair's mean), colours ac381b1a / 7a9de1fd, mask 94e9dc56. Same
# sizes / formats (VQ), so VRAM and heap are unchanged. After fol24 (it replaces the pack). With props24 / pui24 (also fol24 packs) the
# coordinator composes one pack: build_leonhair24.py takes any input pack (RECIPE.txt). Private store /root/re4data/private/leonhair24-20261024 (C: twin without the pack).
LH24D = os.environ.get('LH24D', '/root/re4data/private/leonhair24-20261024')
if os.path.isdir(LH24D):
    DATA['leonhair24'] = {'dc/tex.pak': LH24D + '/dc/tex.pak'}
    PAK_DERIVED['leonhair24'] = LH24D + '/pak-derived.json'
# leonatl24 (lane purge-cast24 10-24, GC purge; data only; user approved the pl00 look 10-25): leonhair24's pack with Leon's
# atlases ec255e66-76812316 (pl00 jacket) and 7506e95f-68cf2211 (pl08) re-made from the PS2 pl00 / pl08 pictures through charbake
# (cb_atlas_gc.py / atlas_ps2.py over PS2 sources, LVQ, headroom 2x): same keys, sizes, VQ formats (pl08 mipmapped), UVs.
# After leonhair24; build_leonatl24.py takes any input pack. Private store /root/re4data/private/leonatl24-20261024 (RECIPE.txt).
LA24D = os.environ.get('LA24D', '/root/re4data/private/leonatl24-20261024')
if os.path.isdir(LA24D):
    DATA['leonatl24'] = {'dc/tex.pak': LA24D + '/dc/tex.pak'}
    PAK_DERIVED['leonatl24'] = LA24D + '/pak-derived.json'
# res22c (lane codex22, 10-22, data only): dc/resident.bin = mip22's remapped file + the listed keys it lacks
# (mip22b ships the same resident.bin and remap; vram/resident_keys.py extend <out> mip22/dc/resident.bin mip22/dc/resident-remap.tsv vram/resident/r*.tsv; same inputs,
# same bytes). Carries the first-use keys (HUD ammo digits in r000, shot effects, first Ganado pictures). Ships the remap
# table beside it for the coverage gate. After mip22 / mip22b; release discs only (not in KSETS, like mip22). 10-22: 5,520 records
# (13 added: r000 HUD digits 2-9 + muzzle flash 148d2ff5 / 3a866b91; r100 983d1064 96f42df9; r101 cf2208cd), sha256 b81231ff.
RES22CD = os.environ.get('RES22CD', '/root/re4data/private/res22c-20261022')
DATA['res22c'] = {'dc/resident.bin': RES22CD + '/resident.bin'}
# res24g (lane purge-cast24 10-24, GC purge; data only): res22c without the 29 never-drawn GameCube player/enemy keys of
# game/platform/preload_skip_gcidle.inc (61 records; r207 / r310 rows kept), with res22c's remap table. Ships with
# PRELOAD_SKIP_GCIDLE=1. After res22c. Private store /root/re4data/private/res24g-20261024 (RECIPE.txt, sha256 6b5c2c7a).
RES24GD = os.environ.get('RES24GD', '/root/re4data/private/res24g-20261024')
if os.path.isdir(RES24GD):
    DATA['res24g'] = {'dc/resident.bin': RES24GD + '/resident.bin'}
# Lane fix-r10d-speed23 (10-23, #55 r10d merchant cave, approximation): r10dlod23 = r10d's PS2 world mesh rebuilt with
# offline LOD for the clusters that had none and 3 m clusters (ps2_room_r4im.py, ch21l inputs and light, + --lod-cluster
# 3000 --lod-min-gain 0.8 --lod-uv-guard 0.05 --lod-floor 60). Same parts and placements as ch21l (ps2-world.r4pw
# byte-identical), so mip22b's rekeyed r4pw still applies. After mip22b. Hut view MODELLED: TA params 1.69 -> 1.06 MB,
# triangles 37.5k -> 21.7k. Private store copy: re4-assets-private/r10dlod23-20261023 (RECIPE.txt, SHA256SUMS).
R10DLOD23D = os.environ.get('R10DLOD23D', '/root/re4data/private/r10dlod23-20261023')
# Its ps2-world.ids carries mip22b's physical r4pw crc: a mesh outside the rect21 provenance certificates keeps that crc,
# and without the file PS2DYN logs "ids=header" (the 61 dynamic placements stop following their objects).
DATA['r10dlod23'] = {'dc/native/r10d/ps2-world.%s' % x: R10DLOD23D + '/dc/native/r10d/ps2-world.%s' % x for x in ('re4mesh', 'ids')}
# r10dbake23 (same lane, step 2 "mostly static and pregenerated"): r10dlod23's recipe + ps2_room_r4im.py --bake-static: the
# 167 static placements (scroll id 254) as one world-space mesh, parts by material and 3 m clusters; the 61 placements with
# an id < 250 stay their own. 228 -> 62 placements, 285 -> 155 parts. r4pw rekeyed to mip22b's texture keys
# (tools/d367/ps2world/r4pw_rekey.py) and its ids. Replaces r10dlod23 in the data line (use one of the two).
R10DBAKE23D = os.environ.get('R10DBAKE23D', '/root/re4data/private/r10dbake23-20261023')
DATA['r10dbake23'] = {'dc/native/r10d/ps2-world.%s' % x: R10DBAKE23D + '/dc/native/r10d/ps2-world.%s' % x
                      for x in ('re4mesh', 'r4pw', 'ids')}
# ps2snd24 (lane purge-audio24, 2026-10-24, GC asset purge; data only, no knob, no AICA layout or size change): the
# chapter 1 + r200 sound banks (etc/core.das, em/pl00 pl08 pl0f pl11, the weapon banks, the room .dar ROOM/FOOT banks,
# the rooms' enemy banks, ss/cmn/title.snd, bgm/bio4midi.dat) and bgm/aica_str.dat with PS2 PCM written into the
# prebuilt AIC1 images in place (tools/ps2_audio.py; map: same cue number on both versions -> GC sample / PS2 VAG).
# 65 files (wep19 and em2a unchanged: no PS2 or no prebuilt bank), every one the size of the release file it replaces. Made from the RELEASE disc's final files (cand-590b8f5f),
# so it must be the LAST set touching these paths (after objs13d, snd16, ch21r, ash21, ...); regenerate if a later set
# changes one of them. RECIPE.txt and the maps (_map/) are in the store.
PS2SND24D = os.environ.get('PS2SND24D', '/root/re4data/private/ps2snd24-20261024')
DATA['ps2snd24'] = {p: PS2SND24D + '/' + p for p in (
    'bgm/aica_str.dat', 'bgm/bio4midi.dat', 'etc/core.das', 'ss/cmn/title.snd',
    'em/em11.drs', 'em/em12.drs', 'em/em13.drs', 'em/em15.drs', 'em/em16.drs', 'em/em17.drs', 'em/em18.drs',
    'em/em21.drs', 'em/em22.drs', 'em/em23.drs', 'em/em24.drs', 'em/em26.drs', 'em/em27.drs', 'em/em28.drs',
    'em/em29.drs', 'em/em2b.drs', 'em/em2e.drs', 'em/em2f.drs', 'em/em35.drs',
    'em/pl00.drs', 'em/pl08.drs', 'em/pl0f.drs', 'em/pl11.drs',
    'em/wep01.drs', 'em/wep02.drs', 'em/wep07.drs', 'em/wep09.drs', 'em/wep11.drs', 'em/wep13.drs',
    'em/wep20.drs', 'em/wep21.drs', 'em/wep24.drs',
    'st2/r200.dar') + tuple('st1/%s.dar' % r for r in (
    'r100', 'r101', 'r102', 'r103', 'r104', 'r105', 'r106', 'r107', 'r108', 'r109', 'r10a', 'r10b', 'r10c', 'r10d',
    'r10e', 'r10f', 'r111', 'r112', 'r113', 'r117', 'r118', 'r119', 'r11a', 'r11b', 'r11c', 'r11d', 'r11e', 'r11f'))}
# Lane purge-weapons24 (10-24, GC purge, coordinator decision C): wep24 = Leon's weapon archives with the PS2 weapon
# models and pictures (tools/d367/ps2cast/ps2_weapons.py + ps2_items_tex.py). Each em/wepNN.drs is the release's own file
# (image d28b3cfc, with its sound bank and compacted REL) with the drawn weapon BINs rebuilt from the PS2 wepNN.dat
# in their GC slots (same offsets / sizes, GC joints and part headers) and the weapon TPL records rekeyed to the PS2
# pictures (loose dc/tex packages). Motions, REL, sounds, Leon's hand BINs unchanged. 19 files, 48 BINs, 43 pictures;
# wep05 (Broken Butterfly) stays GC (PS2 bone 1 rest differs by 15 mm). Last in the data line: it replaces any earlier
# em/wepNN.drs. Private store copy: re4-assets-private/wep24b-20261025 (10-25: + fill_empty_parts, the Test 24 heap-4 fix; RECIPE.txt, SHA256SUMS, provenance.tsv).
WEP24D = os.environ.get('WEP24D', '/root/re4data/private/wep24b-20261025')
DATA['wep24'] = {'em/wep%s.drs' % n: WEP24D + '/em/wep%s.drs' % n
                 for n in ('01', '02', '03', '04', '06', '07', '08', '09', '10', '11', '12', '14', '15', '16', '17', '18',
                           '20', '21', '24')}
DATA['wep24']['tex'] = WEP24D + '/tex'
# wep24ss (same lane, added scope 10-24): the sub screen's weapon models (inventory / examine, ss/cmn/ss_wepNN.dat,
# Leon's ss_wep00..17) rewritten the same way (ps2_weapons.py convert-ss on the release's own files): 16 files, 30 BINs,
# 26 pictures. Leon's hand BINs (attach 9 / 15) unchanged. Use WITH wep24: its tex/ holds only the 2 keys wep24 lacks.
# GC left: ss_wep05 / em/wep05 (Broken Butterfly), tools/d367/ps2cast/weapons-gc-allow.tsv. Store copy:
# re4-assets-private/wep24ssb-20261025 (10-25: + fill_empty_parts; RECIPE.txt, SHA256SUMS, provenance.tsv).
WEP24SSD = os.environ.get('WEP24SSD', '/root/re4data/private/wep24ssb-20261025')
DATA['wep24ss'] = {'ss/cmn/ss_wep%s.dat' % n: WEP24SSD + '/ss/cmn/ss_wep%s.dat' % n
                   for n in ('00', '01', '02', '03', '04', '06', '07', '08', '09', '10', '11', '12', '14', '15', '16', '17')}
DATA['wep24ss']['tex'] = WEP24SSD + '/tex'
# pmwep24 (lane purge-motion24 10-24, GC purge, data only): wep24's weapon archives with their FCV/SEQ motion from PS2
# BIO4DAT.AFS wepNN.dat (tools/d367/motion/ps2_motion_prepared.py rewrite + verify, bodies laid out again; models, pictures,
# REL and sound banks kept). Only the 10 archives whose motion changed (wep02 07 09 10 12 16 17 18 21 24); wep04
# (Blacktail) is not converted (its own fix lane). Use WITH wep24, after it. Store: re4-assets-private/pmwep24-20261024.
PMWEP24D = os.environ.get('PMWEP24D', '/root/re4data/private/pmwep24-20261024')
if os.path.isdir(PMWEP24D):
    DATA['pmwep24'] = {'em/' + _f: '%s/em/%s' % (PMWEP24D, _f) for _f in sorted(os.listdir(PMWEP24D + '/em'))}
# pmwep24b (same lane, 10-25): pmwep24 re-derived on wep24b (empty PS2 weapon parts carry one zero-area triangle, so no
# part falls to the 128 KB native_model preparation); its wep02 / wep12 BIN slots equal wep24b's byte for byte. Use WITH
# wep24b, after it, instead of pmwep24. Store: re4-assets-private/pmwep24b-20261025.
PMWEP24BD = os.environ.get('PMWEP24BD', '/root/re4data/private/pmwep24b-20261025')
if os.path.isdir(PMWEP24BD):
    DATA['pmwep24b'] = {'em/' + _f: '%s/em/%s' % (PMWEP24BD, _f) for _f in sorted(os.listdir(PMWEP24BD + '/em'))}
    CLASH += [('pmwep24', 'pmwep24b')]
# evdmv24 (lane purge-movies24 10-24, GC asset purge): takes the GameCube evd files of the movie-owned route events off
# the disc (r100 s03 s20 s40 s41 s43 s44, r101 s00 s21 s30, r11f s01 s10, each with its .evq sidecar): 22 files,
# 12,968,300 bytes. Their PS2 movies (dc/movie/*.seq) present the events; ONLY with EVD_MOVIE_NO_READ=1 (r100 / r101
# no longer preload them; r11f reads none while its movies are on the disc). r100 s01 / s02 / s42 (no PS2 movie) and
# r11c's PS2-size evd stay. Knob-off programs must not stage it (r101 would open a missing file). Remove-only: no store.
DATA['evdmv24'] = {'remove': ['evd/%s.evd%s' % (n, x) for n in (
    'r100s03', 'r100s20', 'r100s40', 'r100s41', 'r100s43', 'r100s44', 'r101s00', 'r101s21', 'r101s30',
    'r11fs01', 'r11fs10') for x in ('', '.evq')]}


# t24pak (lane compose-test24 10-24, Test 24 composition): the tex.pak sets re-derived as ONE chain, each on the previous
# output (tools/d367/vram/pak_chain.py: every set's own pak-derived.json delta, added keys + re-made keys, applied to the
# running pack; no key is touched by two sets): mip22b 5bba464a -> fol24 35eba5c2 -> pui24 7fd3027f -> pfx24 7a54e971 ->
# pui24s b21f13ed -> props24 200b3bab -> props24p 8666802e -> atlas24 f0e1544e -> props24b 0f85cab4 -> props24l
# 0f85cab4 -> props24x 437fc79d -> leonhair24 1b26f579 -> leonatl24 5e0b72b8 (7341 keys) -> wep24 (pack_add of the
# wep24 + wep24ss loose tex/ pictures, so pak17's drop-loose holds; NOTEX = the set stages no loose pictures). The stores' own packs forked
# at fol24 (props24*, leonhair24) or pui24s; with T24PAK present every set stages its chain pack and chain sidecar
# instead (room archives and other files unchanged). Store /root/re4data/private/t24pak-20261024 (RECIPE.txt, SHA256SUMS).
T24PAKD = os.environ.get('T24PAKD', '/root/re4data/private/t24pak-20261024')
if os.path.isdir(T24PAKD):
    for _s in sorted(os.listdir(T24PAKD)):
        if _s in DATA and os.path.isfile('%s/%s/dc/tex.pak' % (T24PAKD, _s)):
            DATA[_s]['dc/tex.pak'] = '%s/%s/dc/tex.pak' % (T24PAKD, _s)
            PAK_DERIVED[_s] = '%s/%s/pak-derived.json' % (T24PAKD, _s)
        if _s in DATA and os.path.isfile('%s/%s/NOTEX' % (T24PAKD, _s)):
            DATA[_s].pop('tex', None)   # its loose pictures are in the chain pack (wep24: pack_add of wep24 + wep24ss tex/)
# t24prune (lane compose-test24 10-24, Test 24 disc fit): the composed line's tex.pak with its dead keys dropped
# (vram/texpak_live.py <final tree> --write-pak, same package bytes for every live key). LAST in the data line; built from
# the tree of everything before it, so rebuild it whenever an earlier set changes. pak-derived.json: base = leonatl24's chain pack.
T24PRUNED = os.environ.get('T24PRUNED', '/root/re4data/private/t24prune-20261024')
if os.path.isfile(T24PRUNED + '/tex.pak'):
    DATA['t24prune'] = {'dc/tex.pak': T24PRUNED + '/tex.pak'}
    PAK_DERIVED['t24prune'] = T24PRUNED + '/pak-derived.json'
# Mendez door-demo knob + data set: from lane fix-mendez-door24 (placeholder; not in Test 24 recipe yet).

# nostd103 (lane t25-fixes 10-25, Test 25 item 2; coordinator: no GameCube assets wins): takes r103's Standard set off the
# disc. Its index (4,280 B) is over the reader limit (native_static.cpp kStdText=4096) and was rejected on every disc
# since 10-19, and accepting it would bring in GC-derived scenery (low/MAINSCENARIO, a LOD of the GC package) and 19
# texlow pictures made from GC textures (shared with no other room). r103 keeps Original packages + the PS2 world; the
# log line becomes "index.txt missing: Original packages". Remove-only: no store.
DATA['nostd103'] = {'remove': ['dc/native/r103/low/%s' % f for f in ('index.txt', 'MAINSCENARIO.re4mesh', 'plan.json')] + [
    'dc/texlow/%s/%s.re4tex' % (k[0], k) for k in (
        '255f85b3-495d7d69 3628abf0-44e6d158 3a43023f-cf202672 570e2032-fcc53f7c 589a31e5-8ef2a5cd 5c900ef9-0eeea1a0 '
        '6836912e-e089be7e 73aed70b-db3cc2dc 79faed7d-de7a1023 86c0121b-841ef8be 8c58ec0d-96eacb5f 9ec02924-b15bf85a '
        'a3943bb1-eec75484 b2372831-53c12477 b52b2722-ad9a1eff c1eb66a7-93b9292b e831a98f-ace53a55 f47bd095-ec43c743 '
        'fd3d8794-bb70f519').split()]}

# pmrest25 (lane purge-motion25 10-25, GC asset purge: the last motion clips the round-8 census lists): em21 (dog), em23
# (crow), em2a, pl01 and the room archives r100 / r103 / r106 / r11e with every FCV / SEQ member from the PS2 version
# (BIO4DAT.AFS emNN.dat / pl01.dat / rNNN.dat; tools/d367/motion/ps2_motion_prepared.py rewrite --bare for room archives,
# --map for r100's shifted PS2 order). em23 / em2a / r11e are byte-identical to the release (their clips already equal the
# PS2 entries; staged so the motion store proves it). Data only. Built from the RR candidate tree of t15/int 9c2c83db:
# LAST in the data line (after nostd103). Store: re4-assets-private/pmrest25-20261025 (RECIPE.txt, SHA256SUMS).
PMREST25D = os.environ.get('PMREST25D', '/root/re4data/private/pmrest25-20261025')
if os.path.isdir(PMREST25D):
    DATA['pmrest25'] = {'em/%s.drs' % _e: '%s/em/%s.drs' % (PMREST25D, _e) for _e in ('em21', 'em23', 'em2a', 'pl01')}
    DATA['pmrest25'].update({'st1/%s.arc' % _r: '%s/st1/%s.arc' % (PMREST25D, _r) for _r in ('r100', 'r103', 'r106', 'r11e')})
    # the room archive the game reads is the .dar's type-0 record (the .arc copies are staged for consistency)
    DATA['pmrest25'].update({'st1/%s.dar' % _r: '%s/st1/%s.dar' % (PMREST25D, _r) for _r in ('r100', 'r103', 'r106')})
# pmash25 (same lane): Ashley em/pl11.drs (the release's pl11-hot bounded archive) with its motion from PS2 pl11.dat, the
# one new dc/mot key it streams, and the GC key no archive references any more off the disc (remove.txt). ONLY with
# MOTION_PS2_PL11=1 (its pl11-hot profile row); a program without it refuses the archive. After pmrest25.
# Store: re4-assets-private/pmash25-20261025.
PMASH25D = os.environ.get('PMASH25D', '/root/re4data/private/pmash25-20261025')
if os.path.isdir(PMASH25D):
    DATA['pmash25'] = {'em/pl11.drs': PMASH25D + '/em/pl11.drs'}
    DATA['pmash25'].update({'dc/mot/' + _k: '%s/dc/mot/%s' % (PMASH25D, _k) for _k in sorted(os.listdir(PMASH25D + '/dc/mot'))})
    DATA['pmash25']['remove'] = [_l.strip() for _l in open(PMASH25D + '/remove.txt') if _l.strip()]


if __name__ == '__main__':
    main()
