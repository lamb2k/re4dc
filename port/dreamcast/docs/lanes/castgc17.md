# CAST-GC: characters drawn by the GameCube path (lane castgc17, 2026-10-17)

User 10-17: "why do we keep falling back to gamecube models, that shouldn't be occurring". A room without a PS2
package, or a package that declines (certificate, roles, texture limit, memory), used to draw the GameCube model
silently. CAST-GC makes that a gate failure, like LEON-GC for Leon.

## The check

- `tools/d367/cast_gc.py <run-output.txt>... [--allow castgc/allow.tsv] [--json OUT]` reads the native census of a
  build with `NATIVE_MODEL_REGISTRY_CENSUS=1` (use `NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=30` for <= 60 s runs, so the
  last report lands before the deadline). From the `NMRS` / `NMRD` / `NMRU` / `NMRPACK` lines it prints room, model,
  path and reason:
  - **PS2**: drawn by a native plan (Leon plan, the PS2 Ganado cast, a registry package).
  - **GC**: the transaction returned the model to the source (GameCube) path, with the reason. That is either "no
    package" (no plan for the id), the Ganado cast not taking a Ganado-class id, or a registry descriptor declining
    (roles / skeleton / layout / semantics / certificate / acquire / skin from `NMRD`).
  - **MIXED**: some passes native, some GameCube.
  - **CROWD-SKIP**: every pass skipped by the crowd policy (not drawn, not GC).
- Verdict: any GC or MIXED character / enemy (model id 01..7f) that `tools/d367/castgc/allow.tsv` does not list
  FAILS (exit 1). Leon (id 00) is listed but judged by LEON-GC. A log without census lines exits 2 (not a pass).
- The allowlist is short and reviewed. Each line gives room (or `*`), id, reason and owner, and is added only with the
  coordinator's review. It starts empty.
- Hooks:
  - `test15/t15-build.sh` mW check arms carry the census (MC), as they carry MCHECK_LEONGC.
  - `fullplay/fp_check.py` fails a segment on an unlisted GC character (category gc-fallback; known-issues apply). A
    build without the census gets a "CAST-GC not judged" note.
  - `test11/t-run.sh` prints `castgc=<rows>` in its summary line.
- The census cannot tell "the Ganado cast has no plan" from "its layout / semantics / acquire failed" (both log plan
  G, declined). An `ACTOR_TRANSACTION_DIAG=1` build names the step (`ATX_M ... ev=4:` = no plan).

## Runs (Flycast, emulated; 60 s each; discs deleted after each run)

- Warps: `tools/d367/castgc/warps/<room>.txt`, made by `castgc/mkfix.py` from the warp.py presets, the in-tree warps
  (ch2 kill rigs k-r111 / k-r113 / k-r10f / k-r11d / k-r200) and stage_route door entries (r10b, r11b). Every warp
  has god mode. Fixtures go through `texchk/fixture_arm.py`: STAGE_OVL images need the stage overlays.
- **Test 16:** the test 16 source (tag test-72871476-20261016), T15REC with T15_FS="" T15_WV="", data T16_DATA, warp
  arm + census. Labels g16rW (period 150, runs c1-*) and g16prW (period 30, runs e1-*).
- **Test 17:** t15/int f7782076, ch2/ch2-build.sh rW (T15REC + CH2REC), data T17_DATA, + census. Labels g17rW
  (period 150, runs b1-* / d1-*) and g17prW (period 30, runs f1-*); g17xrW adds ACTOR_TRANSACTION_DIAG=1 (run x1-r108).
  - Cap as shipped (cap 6): cap 4 (item 15, T15_AC) is not on f7782076. The cap changes how many are alive, not
    which path draws them.
  - The test 17 fixtures stage data set ch2's resident.bin in warn mode. RE4DC_RESIDENT_STRICT=1 refuses it on
    f7782076: 22 chapter 4 lists (ch4found, r206..r22b) are short. Repack resident.bin before the release fixture.
- Evidence: `C:\Flycast-Evidence\re4-dreamcast\castgc17-20261017\<run>`.

## Result: what still draws the GameCube model

| Room | Character | Test 16 | Test 17 | Reason |
|---|---|---|---|---|
| r108 | em17 (Ganado-class, 34 parts, 4 infos) | **GC**, every pass (32,490) | **GC**, every pass (25,290); **PS2 with r108p** (fixed 10-17, below) | No plan: r108 spawns em17 type 0xc holding a weapon (body 0x1cd, head 0x1cf, TPL 0x1ce, hands 0x1c0 + grip 0x1c8). The shipped r108 package has the non-pool descriptor ganado-em17-0c (hands 0x1c0 / 0x1c5 only), so the registry refused it on role rows (NMRU roles) and the GameCube model drew. r111 / r113 draw the same id through the pool descriptor ganado-em17-0cp. |
| r200 | em12 (Ganado) | not on the test 16 route | **GC, 3 passes** (the rest crowd-skipped); allowlisted | Not a fresh-send transient (corrected 10-17). The model existed from the start of the window (ATX_M f=455); the kill rig killed it in 1 hit and its head info then pointed at BIN 0x1bf (447, ATX_INFO why=2 "no recorded asset"). 447 is the small BIN after appearance 1's head (446): the head-burst stump, the same slot as the reviewed BIN 479 stump of appearance 2 (ps2_ganado_stump.py, ACTOR_GANADO_PS2_STUMP, default off, appearance 2 only). The cast has no stump for appearances 0 / 1 / 3 / 4 (BIN 475 / 447 / 483, em15 460), so a head-burst corpse draws GC until it goes away. The run ended in that window. |

Everything else the census saw drew PS2, in both builds:
- Ganado cast: r101 em15, r111 em17, r11d em16.
- Registry packages:
  - Chapter 1: r103 dog / cows / chicken, r105 / r107 / r10a traps, r108 / r109 / r105 crows, r10a snake, r118 wolves.
  - Chapter 2: r10f / r11c em13 and r112 em18 merchants, Ashley (ashley11) in r111 / r112 / r113 / r11f, the r11d em16
    Ganados and cart, the r200 truck.

em12 in r103 / r107 / r10a / r11a was crowd-skipped in the window (not drawn, not GC).

Coverage limits (60 s runs, about 1,000-1,500 UI frames in a room):
- r100: the s03 movie takes the run. Its crows / dog / traps were admitted natively (NMRM admit).
- r104, r106, r117, r119, r10b, r102: only Leon reached the census in the window; their enemies did not come into view.
- r113 em17 and r200 em12 were mostly crowd-skipped.
- r11b: no census line (no actor reached the transaction).
- r10c and r10e are not on the release disc (no st1/r10c.dar / r10e.dar in the package base tree): not route rooms.
- r11e: El Gigante was not reached in 60 s.

## 10-17 follow-up

### r108 em17: fixed (data set r108p)

- Package: `model-registry/ps2-ch1-r108p.json` = ps2-ch1-r108 with ganado-em17-0c replaced by the pool descriptor
  ganado-em17-0cp (as r113p / r118p; NATIVE_MODEL_REGISTRY_POOL=1 is already in the recipe). Built with
  `model_registry.py ps2-ch1-r108p.json <out> --tree <checkout> --package-room 108 --pool --wide-identity` over the cast
  dir `regcast-r108p` (the shipped r108 cast dir plus ganado-em17-0cp from regcast-ch2p; the shipped spec over it
  reproduces the shipped package 6a059ff1 byte for byte). registry.re4nmr 99,872 B (shipped 72,896 B), sha256
  cd46d46c2d504305...; its 4 textures are already in pak17's tex.pak (no loose texture).
- Data set `r108p` in t11-fix.py (private data: `/root/re4data/private/castgc17-20261017/r108p`, R108PD), staged before
  pak17: `T17_DATA = T15_DATA + ',ch2,cast16,r108p,pak17'`. The release `--disc-sets` line becomes
  `snd16,water16i,vq16w,fsh,ch2,cast16,r108p,pak17`. The only staged difference is `dc/native/r108/registry.re4nmr`.
- Gates (Flycast, f7782076 + census period 30, 60 s, evidence `castgc17-20261017\p1-*`):

| Run | Fixture | em17 in r108 | Kills |
|---|---|---|---|
| p1-p108 | r108 with r108p | CAST-GC PASS, PS2 21,090 rows, 0 GC | - |
| p1-kp108 | r108 kill rig (`kill 0x17 300 0x108 1`, `killrep 30 90`) with r108p | PASS, PS2 16,830, 0 GC | 9 kills, 18 kill lines |
| p1-k0108 | the same rig without r108p | GC 16,830 (the old failure) | the same 18 lines: same targets, frames, hits |

- Heap 4 used after the r108 package opens: +27,712 B (7,509,952 vs 7,537,664 free). Other rooms do not read the
  file, so STRICT outside r108 is untouched; the program image does not change.

### r200 em12: allowlisted (head-burst stump)

- castgc/allow.tsv: `r200  12` with reason and owner castgc17. The same stump GC will show in any room whose run blows a
  Ganado head (any appearance; appearance 2 too while ACTOR_GANADO_PS2_STUMP is off). The fix is a PS2 stump per
  appearance (convert BIN 475 / 447 / 479 / 483, em15 460, as ps2_ganado_stump.py did 479) with ACTOR_GANADO_PS2_STUMP
  on; that is a conversion and review item, not a one-line fix.
- The diag that found it (ATX_TPL / ATX_TPL_INFO: BIN and TPL entry numbers of each info, inside
  RE4DC_ACTOR_TRANSACTION_DIAG) is kept as a patch, not landed: `/root/probe/lanes-20261016/castgc/k/atx-tpl-diag-20261017.patch`.
