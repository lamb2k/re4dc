#!/usr/bin/env python3
"""mkch2data.py OUTDIR [--copy] : the chapter 2-2 / 2-3 data set 'ch2' for test11/t11-fix.py (lane ch2code16, 2026-10-16).

ch2 = what the 10-14 route fixture (lane ch22-1014 fix/route-v7.json: the test 10 package + every 2-2 / 2-3 room's data from
Codex's first-pass fixtures and the ch22 lane's AICA banks / streams) adds over the test 10 package, layered on test 15's data
(T15_DATA), with these resolutions (CH2-CODE-COMPLETE-20261016.md "Data set ch2"):
  - files test 15 already replaces keep test 15's bytes: the r117 world (blackps2 relight), em17 (PS2 accessories acc12),
    em2a (prep14), texture 60079405-d856504e (cast15 r118 pool); except pl11: route-v7's bounded Ashley (PREFER_V7,
    heap 4 in r118 after the rescue; same PS2 texture keys);
  - bgm/aica_str.dat = aica_banks.py --streams ch2 (OUTDIR/str-ch2, built separately; game AICA_STR_ENT_MAX >= 53);
  - r11d / r11e: the room archives compacted + released against their converted room package (prep-room.sh; the GC GX
    payload leaves the resident archive: r11d 4,276,096 -> 1,219,488 B, r11e 4,011,360 -> 1,078,976 B of heap 4), the
    ch22 lane's AICA room banks transplanted (aica_transplant.py), their MAINSCENARIO packages and compact textures;
  - em16 (r11d Ganados): the GC archive prepared like em11 (prepare_enemy_motions.py Ganado contract, textures + cold
    motions: heap 4 4,246,528 -> 1,445,792 B), its AICA bank transplanted, its dc/mot keys and textures;
  - r113.dar: its ROOM bank refit 11025 -> 8000 Hz so em17 fits the room arena (lane/fit-r113.py);
  - the 201 base-disc pictures route-v7 un-removed (2-2 / 2-3 rooms read them) stay on the disc.
Writes OUTDIR/ch2-data.json {"replace": {disc path: source}, "unremove": [...], "provenance": ...}; --copy copies every
source under OUTDIR/files (durable, ext4) and points the map there.
"""
import hashlib, json, os, shutil, subprocess, sys, importlib.util as iu
from pathlib import Path

HERE = Path(__file__).resolve().parent
T11 = HERE.parent / 'test11' / 't11-fix.py'
V7 = '/root/probe/lanes-20261014/ch22/fix/route-v7.json'
T10 = '/root/probe/lanes-20261014/t10s/fix/pkg-t10stP.json'
LANE = '/root/probe/lanes-20261016/ch2'
CX = '/root/probe/codex-cx-fixtures-20261013/output'
KEEP_T15 = {'dc/native/r117/ps2-world.ids', 'dc/native/r117/ps2-world.r4pw', 'dc/native/r117/ps2-world.re4mesh',
            'dc/tex/6/60079405-d856504e.re4tex', 'em/em17.drs', 'em/em2a.drs'}
# Files where route-v7's bytes replace test 15's: pl11 = Codex's bounded 'pl11-r11f' Ashley (prepare_enemy_motions.py
# --bounded-profile, motions cold, top-level textures external): heap 4 384,064 B body vs test 15's textures-only
# archive (828,384 B resident). With test 15's, r118 after the rescue (em17 + em3b + em22 + Ashley) ran heap 4 out
# ("ModelInit() Parts allocate was failed", "cSubChar::modelSet() failed", heap4 free 352 B: run g4, 10-16); with the
# bounded one it keeps 334,720 B free (g5). Both resolve Ashley's textures to the same PS2 keys (2353f21e, 2c9c252a,
# 56d70169, bc5bb46e: test 15's dc/tex files, loaded in both runs), so the PS2 Ashley look stays. MOTION_BOUNDED_R11F.
PREFER_V7 = {'em/pl11.drs'}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    out = Path(sys.argv[1]); copy = '--copy' in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    s = iu.spec_from_file_location('t11', T11); m = iu.module_from_spec(s); s.loader.exec_module(m)
    full = out / 't15full.json'
    subprocess.run([sys.executable, str(T11), 't10stP', str(full), '--data', m.T15_DATA], check=True, stdout=subprocess.DEVNULL)
    A = json.load(open(T10)); B = json.load(open(full)); R = json.load(open(V7))
    ra, rb, rr = A['replace'], B['replace'], R['replace']
    rep, notes = {}, []
    for k, v in sorted(rr.items()):
        if ra.get(k) == v or k in KEEP_T15:
            continue
        if k == 'bgm/aica_str.dat':
            continue
        if k in rb and rb[k] != ra.get(k) and k not in PREFER_V7:
            if sha(rb[k]) == sha(v):
                continue
            raise SystemExit('unresolved conflict with test 15 data: %s (t15 %s, v7 %s)' % (k, rb[k], v))
        rep[k] = v
    # r11d / r11e released rooms + transplanted AICA banks, their packages and compact textures
    for r in ('r11d', 'r11e'):
        rep['st1/%s.dar' % r] = '%s/snd/%s.dar' % (LANE, r)
        rep['st1/%s.arc' % r] = '%s/rooms/%s/released/st1/%s.arc' % (LANE, r, r)
        rep['dc/native/%s/MAINSCENARIO.re4mesh' % r] = '%s/rooms/%s/package/MAINSCENARIO.re4mesh' % (LANE, r)
        for p in sorted(Path('%s/%s/ancillary-c3d2f4cd6f00/tex' % (CX, r)).glob('*.re4tex')):
            k = 'dc/tex/%s/%s' % (p.name[0], p.name)
            if k in rb:  # one key, one picture: test 15's bytes ship (a re-encode of the same image)
                if sha(rb[k]) != sha(str(p)):
                    notes.append('%s: %s differs from test 15, test 15 kept' % (r, k))
                continue
            rep.setdefault(k, str(p))
    # r113: its own room banks refit so em17 (the Ganados' voices) fits the arena (lane/fit-r113.py)
    f113 = '%s/snd/fit113/out/st1/r113.dar' % LANE
    if os.path.exists(f113):
        rep['st1/r113.dar'] = f113
    else:
        notes.append('st1/r113.dar refit not built (lane/fit-r113.py): r113 Ganado voices silent')
    # lane cast16 requests (10-16): Ashley's PS2 partner packages for the 2-2 / 2-3 rooms (ps2lib cast rows; her
    # archive stays the bounded pl11 above), and r113's em17 pool registry (reg-113p: plan R, 0 declines) + its textures
    PL = '/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/cast'
    # r11f is held back: with its partner package the Mendez segment logs "IKInit(): missing Root", "MotionMoveCore():
    # Em[3h], Invalid parts" / "MODEL HAS NO PARTS" after s11 and the game resets (runs v2/v7/v9 s-mendez; h2/h3 without
    # it pass). r11f keeps the GameCube Ashley until cast16 fixes the package.
    for r in ('r111', 'r112', 'r113', 'r11c'):
        rep['dc/native/%s/partner.re4nmr' % r] = '%s/%s/ashley-pl11/dc/native/%s/partner.re4nmr' % (PL, r, r)
    R113P = '/root/probe/lanes-20261015/ps2cast/conv-ch2/reg-113p'
    rep['dc/native/r113/registry.re4nmr'] = R113P + '/package/r113/registry.re4nmr'
    for p in sorted(Path(R113P + '/tex').glob('*.re4tex')):
        k = 'dc/tex/%s/%s' % (p.name[0], p.name)
        if k in rb or k in rep:   # one key, one picture (0e80c998: reg-108's bytes ship, cast16 10-16)
            if sha(rb.get(k) or rep[k]) != sha(str(p)):
                notes.append('reg-113p: %s differs, the existing copy kept' % k)
            continue
        rep[k] = str(p)
    # VRAM (coordinator/user rule 10-16: VQ room textures by default when it frees needed capacity, PSNR floor ~29 dB,
    # UI / text / alpha-critical stay 16-bit): dc/tex.pak = test 15's vq16cs pak + the 89 chapter 2 pictures of
    # vram/vq16-ch2.txt as full-codebook VQ (vram/vq16c-texpak.sh; LANE/vram/vqch2), and dc/resident.bin = test 15's
    # chapter 1 lists + the chapter 2 room lists vram/resident/r1xx.tsv / r200.tsv (resident_keys.py pack; LANE/vram/res)
    for k, f in (('dc/tex.pak', LANE + '/vram/vqch2/tex-vq16c.pak'), ('dc/resident.bin', LANE + '/vram/res/resident.bin')):
        if os.path.exists(f):
            rep[k] = f
        else:
            notes.append('%s not built (%s): test 15 file stays' % (k, f))
    # em16
    rep['em/em16.drs'] = '%s/snd/em16.drs' % LANE
    for p in sorted(Path('%s/em16/prep-em16/mot' % LANE).glob('*.fcv')):
        rep['dc/mot/' + p.name] = str(p)
    for p in sorted(Path('%s/em16/tex-em' % LANE).glob('*.re4tex')):
        k = 'dc/tex/%s/%s' % (p.name[0], p.name)
        if k in rb:
            if sha(rb[k]) != sha(str(p)):
                notes.append('em16: %s differs from test 15, test 15 kept' % k)
            continue
        rep.setdefault(k, str(p))
    # chapter 1+2 stream file
    st = out / 'str-ch2' / 'bgm' / 'aica_str.dat'
    if st.exists():
        rep['bgm/aica_str.dat'] = str(st)
    else:
        notes.append('bgm/aica_str.dat not built yet (str-ch2): test 15 snd16 file stays')
    unremove = sorted(set(A.get('remove', [])) - set(R.get('remove', [])))
    for k, v in rep.items():
        if not os.path.exists(v):
            raise SystemExit('missing source %s -> %s' % (k, v))
    if copy:
        fd = out / 'files'
        for k, v in sorted(rep.items()):
            d = fd / k
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists() or sha(str(d)) != sha(v):
                shutil.copyfile(v, d)
            rep[k] = str(d)
    prov = {'v7': V7, 't10': T10, 'keep_t15': sorted(KEEP_T15), 'prefer_v7': sorted(PREFER_V7), 'notes': notes,
            'count': len(rep), 'bytes': sum(os.path.getsize(v) for v in rep.values())}
    json.dump({'replace': rep, 'unremove': unremove, 'provenance': prov}, open(out / 'ch2-data.json', 'w'), indent=1, sort_keys=True)
    print('ch2 data', len(rep), 'files', prov['bytes'], 'bytes', len(unremove), 'unremoved', notes)


if __name__ == '__main__':
    main()
