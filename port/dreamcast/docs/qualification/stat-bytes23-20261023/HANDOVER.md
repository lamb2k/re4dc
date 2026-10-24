# stat-bytes23 handover (Claude -> local Codex, 2026-10-23)

Branch: origin `wip/stat-bytes23-20261023` at c11a7eea (base t15/int 7b6ad154). Worktree /root/work/lanes/stat-bytes23. Nothing is landed yet.

## Audit method
To find every use, I renamed `cModel::stat` (include/model.h) and compiled every src/**/*.cpp with `-fsyntax-only`. There were 71 hits, which I merged with a grep. Script: scratchpad audit2.sh (copy below). em10 and em35 already have their own knobs, so I left them alone.

## Findings: all GC big-endian word stores or tests, all confirmed bugs on DC
- **Player, in the core and on the route:**
  - player.cpp:359: the `moved` test. It is wrong whenever Leon stands still, so the camera's setPlayerLocation runs every frame.
  - player.cpp:388: parts ang at routine 6/0.
  - pl_class.cpp:926: isKamae (shoulder camera at aim step 0).
  - pl_sub.cpp:1091: PlGetWeaponNo knife (0xB).
  - pl_wep.cpp:596: getMarkerPos. It always returns 0 on DC, so the scope filter08 has no marker.
  - pl_wep.cpp:875: PlCornerCheck (0xD).
  - cockpit.cpp:654/656/699/701: the bullet digits and icon in player routine 0xF (the boat).
- **Partner (Ashley, ch2-2 on):** pl_sub.cpp:539 and pl_npc.cpp:1828, 2535, 2563, 3107, 3117, 3129, 3272, 3962 (partner_stat), 3976.
  - The 3272 test feeds the SubCharGetStatus 0x40000000/0x20000000 bit, which r11e and r11f read.
- **Route overlays:**
  - pl0f.cpp:974: the boat rudder (Del Lago).
  - pl14.cpp:1420: Luis, the scenario kill 0x0400.
  - em2b.cpp:135: El Gigante's EM_RTN (the threat roll at Game_level<=1).
  - em2a.cpp:156: the set-1 dog trap gives critical points when shot.
  - em21.cpp:149/173/633: the r100 trap dog. Off-route today: ANIMALS_OFF=1 means em21.rel is not on the disc.
- **Later content, all harmful:**
  - obj14.cpp:274/280 (bell ckBreak, castle r201/r218) and obj15.cpp:495/540/555 (gatling);
  - em25:1445, em2c:152, em2d (EM_RTN plus 10 stores), em32 (3 stores, 2 tests), em36 (6 stores plus EM_RTN), em38 (EM_RTN/EM_RTN_SET), em39 (6 stores, EM_RTN, 2 tests);
  - st3/r30c.cpp:350 (Ashley stat=0x02000000).
- **Clean (other structs):** snd, roomdata, EtcModel, t_esp, card, sofdec.

## Change (knob STAT_ROUTINE_BYTES, default 0)
- `STAT_BE(x)` in platform/include/re4dc_prelude.h is `__builtin_bswap32` when the knob is on and `(x)` when off. It wraps every constant at the 62 sites above.
- The Makefile sets `GAME_CPPFLAGS += -DRE4DC_STAT_ROUTINE_BYTES=1`.
- `STAT_DIAG=1` (test only):
  - player.cpp logs `STATDIAG selftest/differ/count` (the GC meaning against the raw word, for player and partner sites);
  - em21.cpp logs dog and trap routine changes.
- Knob OFF: the image is 2527654c = release, and every .ovl is identical. Knob ON: the image is 96 B smaller, and memory cost is 0.

## Left to do
- Gates not run: KOS squeeze, h2 s30 340/340, census/TEXCHK, gameplay equivalence (kills, phases, cutscenes) with the knob on.
- Bases are ready at C:\Flycast-Evidence\re4-dreamcast\stat-bytes23\_discs\{sbOg,sbOc,sbNg,sbNc} (O = off, N = on; g = h2/gdemu twin, c = KOS/census twin). Syms are in fixtures\syms-*.txt.
- Before and after for route cases: STATDIAG pairs ran from the QA bases \off and \on.
  - Differences seen: fight and r11e (moved, isKamae on every frame); boat (cockpit bullets, the pl0f rudder, moved, isKamae).
  - ch22a, siege and mendez logged no STATDIAG count lines. Check those logs for the reason (Ashley sites were not hit).
- Still needed: a behaviour repro per route site (for example, boat HUD digits hidden with the knob on), and the console QA disc folder RE4DC-QA23-StatBytes-c11a7eea.
  - The disc zip is built (knob on + diag): /root/work/lanes/stat-bytes23-scratch/zip/RE4DC-QA-Test23-c11a7eea-20261023-GDEMU.zip. It still needs to be unzipped to C: and given a README.
- Still needed: the patch file (git diff 7b6ad154..c11a7eea, minus the WIP history).
- Recipe once gated: CH2 += STAT_ROUTINE_BYTES=1.

## r11f "cDatTbl::GetDat : memory failed[evm7000/evm8300]"
- Evt_R11FS00_Func (st1/r11f.cpp:437-470) calls e->GetMod("evm7000"/"evm8300") while r11fs00 plays as a route movie.
- The in-engine event model table (ModTbl.pWork) is never built, so GetDat logs the error and returns 0, and only the be_flag/CMF toggles of the event models are skipped.
- The QTE (qte=1) and the fight carry on. It is harmless log noise. The fix would be to silence it when ModTbl is unbuilt (optional).

## Tools used
- Builds:
  - `ch2-build.sh rP` with recipe.conf CH2 (+knob);
  - `rr/rr-qa.sh <W with recipe.conf> <tree> <sha> 23 <zipdir|-> <ev>` for the QA bases;
  - `fullplay/fp_twin.sh` + `fp_iso.py extract` + `fp_master.sh` for the g/c bases (scratchpad b1/b2/b3.sh).
- Runs: C:\Flycast-Evidence\re4-dreamcast\stat-bytes23\fixtures\sb-run.sh / sb-pairs.sh (fp_run.py --base --warp [--pad]). Warps were copied from fullplay/segments and ch2/warps.
