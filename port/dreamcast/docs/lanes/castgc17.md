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
| r108 | em17 (Ganado-class, 34 parts, 4 infos) | **GC**, every pass (32,490) | **GC**, every pass (25,290) | No plan: the PS2 Ganado cast does not take r108's em17 and r108 has no registry descriptor for it (ACTOR_TRANSACTION_DIAG: event 4 "no plan" on 120 of 120 passes per report). The same id draws as the PS2 cast in r111. |
| r200 | em12 (Ganado) | not on the test 16 route | **GC, 3 passes** (the rest crowd-skipped) | In the census window right after the kill rig killed a just-sent Ganado still at 0,0,0: a fresh em12 drew GC for a few passes before the cast took it (transient). |

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
