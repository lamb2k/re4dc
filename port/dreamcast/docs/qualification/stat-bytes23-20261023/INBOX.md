# stat-bytes23 INBOX (local Codex, handed over from Claude 2026-10-23, user request)

Goal: find and fix every place that writes an enemy/object routine "stat" word in GameCube big-endian byte order, as one unit under one knob STAT_ROUTINE_BYTES=1 (default 0, knob-off identical). Same bug class as the Mendez freeze, already fixed (EM35_ROUTINE_BYTES, t15/int 7b6ad154): em35_R1_br_Catch wrote 0x010D000n as a GC big-endian word, so Mendez sat in Wait step 0xD forever after any grab. See also GANADO_ROUTINE_BYTES (em10, in the recipe) for the earlier fix of the same pattern.

STATE AT HANDOVER (10-23): the fix is BUILT on wip/stat-bytes23-20261023 c11a7eea (base 7b6ad154): STAT_BE() at 62 stat sites, knob off image 2527654c = release, knob on 96 B smaller, STAT_DIAG=1 test log. NOT yet run: KOS squeeze, h2 s30, census/TEXCHK, gameplay equivalence (disc bases ready in C:\Flycast-Evidencee4-dreamcast\stat-bytes23\_discs), per-site repros on route, console disc folder. QA zip (knob on + diag) at /root/work/lanes/stat-bytes23-scratch/zip/RE4DC-QA-Test23-c11a7eea-20261023-GDEMU.zip.
Start from HANDOVER.md in this folder (written by the Claude lane when it stopped): files audited, findings, WIP branch wip/stat-bytes23-20261023, what is left.

## I-001 finish the audit and fix
Candidates: em36, em39, em2c, em21, em2a, pl_sub, cockpit, pl_npc, pl_wep, obj15, r30c and any other writer of the routine/stat word (grep for the same macro/idiom as the em35 and em10 fixes). For each: confirmed bug / clean / unsure, with the line.
Fix all confirmed ones under STAT_ROUTINE_BYTES=1 (audit fixes go in as one unit; split only on a failing gate).

## I-002 repro and gates
- A repro per confirmed bug where one exists (enemy stuck after a grab/attack/state change), before 1/1 -> after 0.
- Gates: decisions-identical where the bug doesn't fire (r101 bell, seg-mendez kill rig), KOS 48 KiB, GDEMU seed 1, h2 s30 340/340 with heap_before, census of the rooms touched.

## I-003 r11f log line: ANSWERED, skip (harmless: r11fs00 plays as a movie, so the event model table is never built)
Explain "cDatTbl::GetDat : memory failed[evm7000/evm8300]" in r11f: harmless, or a missing event model? Fix only if it shows on screen.

## Hand-back
Branch wip/stat-bytes23-20261023 off origin/t15/int (bbfd1bd0 or newer), origin only, never bruce. Console QA disc C:\Game Dev\Emulators\RE4DC-QA23-StatBytes-<sha8> with a README (which enemy, what to do, what should happen). Short report; Claude lands and sets the recipe.
