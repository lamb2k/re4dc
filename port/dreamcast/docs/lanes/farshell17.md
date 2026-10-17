# Lane farshell17: the far shell leaves heap 4 alone (2026-10-16, test 17)

Branch lane/farshell17 (code ba771dd0, docs d99f49e6, merged onto t15/int 9d008043). Knob FAR_SHELL (recipe group
T15_FS, unchanged: `FAR_SHELL=1`), data set fsh (fsh6: r100 122,363 B, r101 119,744 B). Design of the shell itself:
docs/lanes/farshell16.md.

## The bug that pulled the shell from test 16

FAR_SHELL=1 read `dc/native/r100/far-shell.fsh` into heap 4 (124,512 B with its colour table) at every room entry at
every View distance, Full included (log `FARSHELL ... loaded=1 view=0`). r100 after the ambush is heap 4's tightest
point: right after the s20 movie the after-state enemies load (em21 340 KB, em2a 233 KB) and the work backing for the
s30 Ganados ran out: `work backing: allocation failed`, `EmSetFromList2() Em set failed, Id = 12` twice, 2 Ganados
missing. Test 16 release check (C:\Flycast-Evidence\re4-dreamcast\t16rc-20261016, h2 through s30): heap 4 free at the s30
movie 57,632 B with the shell (arm rW) against 133,408 B with T15_FS="" (nofsW) and 145,696 B on 15.1 (qW).

## Where the shell lives now

Still heap 4 (the bytes say no other home fits), but only while it can be drawn, and it is the first thing to go:

| Rule | Where |
|---|---|
| Read only at View distance Short with mode 1 (Full / Near: never read, 0 B); the option changing to Short reads it at the next world draw, changing away frees it there | far_shell.inc `sync()`, called by every `ps2_open` (room entry and each world draw); option_rows.cpp `re4dc_view_dist_set` |
| Lent to every route movie (freed before `heap_before`, as the PCCULL cell), read again at the first world draw after the movie | native_movie.cpp `open`; route_movie_bridge.cpp `re4dc_far_shell_movie_restore` |
| Heap 4 short: a failed heap-4 `mem_alloc`, or a native static package refused for its 80 KiB reserve or not placed, frees the shell and retries once; the room is marked yielded and is not read again (also on its next entries) until the View distance option changes | main_mem.cpp `mem_alloc`, ui_bridge.cpp `re4dc_static_alloc`, far_shell.inc `re4dc_far_shell_shortfall` |
| Never freed mid-draw (the draw holds pointers into the block): a shortfall during the shell draw is refused | far_shell.inc `Busy` |
| A read refused for heap 4 (`open=heap`) is not retried in that room visit | far_shell.inc `pol.tried` |

In the h2 route at Short (r100 house through the s30 cliff movie) the shell is read at entry (3,250,080 -> 3,125,568),
lent to s03, read again, lent to s20; after s20 the after-state enemies have already taken heap 4 (73,472 B free) and
the read is refused, so r100 shows the plain Short cut from there to the door and the shell holds 0 B at s30. The s30
Ganados get heap 4 as without the shell. The test-only warp line `farshellprobe <room frame>` (one heap-4 request of
all the free bytes) proves the give-back path: r100 after-state entry at Short, `FARSHELL room=100 yields to heap 4:
need=209280 at warp farshellprobe heap=209248`, then `freed bytes=122363 (heap 4 short) heap=333728` (+124,480 B), no
read afterwards (afterSP-fs17crW).

Other homes, measured (bytes, Flycast logs of this lane; not timings):

| Home | Measured | Verdict |
|---|---|---|
| VRAM (vertex data beside the textures) | r100 after the ambush: free 116,736 B, largest block 4,064 B (VRAM room log, h2S-fs17crW f=1623); r101 fight: min free 220,544 B, largest 10,240 B | no: 122 KB contiguous does not fit, and the VRAM rule gives VRAM to textures. The CPU would also read every drawn vertex across the PVR bus |
| Sound RAM | `aica: layout ... 95,552 free (movie reserve 65,536)` | no: 95 KB < 122 KB, and G2 reads are slower still |
| KOS | 48 KiB squeeze gate leaves 11.7 KB in the r101 fight | no: KOS is the tight one |
| Movie-evictable pool | the movies borrow the model preparation cache, LRU motion keys and (s30) the r100 world package: all heap 4 | the shell joins that pool instead: lent to every movie |

## Heap 4 at the s30 movie (Flycast, bytes from `route movie active: id=10030 source_heap=`)

Build t15/int 160802e0 + lane, T15REC (FAR_SHELL=1), fixture T15_DATA (fsh6), h2 warp + pad (fullplay/segments), View
distance by warp line `viewdist`. Control = the same recipe with T15_FS="" (no shell code).

| Arm (image) | Full | Short | Em set failed / allocation failed | s30 |
|---|---|---|---|---|
| fs17nrW, T15_FS="" (control) | 129,312 | 129,312 | 0 / 0 | 340/340 |
| fs17rW, lane code (= the play code + DBG_WARP) | 125,216 | 125,216 | 0 / 0 | 340/340 |
| fs17crW, commit ba771dd0 (adds the DBG_WARP probe line) | 121,120 | 121,120 | 0 / 0 | 340/340 |
| fs17nrT / fs17crT, trace arms | 121,120 / 112,928 | 121,120 / 112,928 | 0 / 0 | 340/340 |
| test 16 rc rW (shell at every View distance) | 57,632 | - | 2 / 4 | 340/340, 2 Ganados missing |

- On one image, Full and Short are byte-identical at s30: the shell holds nothing there.
- Against the T15_FS="" control the knob costs one 4 KiB heap-4 step (two on the trace arm): the image grows (play rP
  _end 8c426ed8 -> 8c428298, +5,056 B; warp +5,184 B) and heap 4 couples to image size in 4 KiB steps (mem.cpp
  ARENA_FIT: the control's KOS slack was 1,528 B, so any growth above that moves one step; RAM-BUDGET-20261015.md). This
  is the static code of the far shell (farshell16 ~3.9 KB + this lane ~1.1 KB), not residency; it cannot get under the
  1 KB line without dropping the feature.

## Gates

| Gate | Result |
|---|---|
| h2 through s30, Full and Short (W arms, table above) | heap 4 at s30 identical Full = Short; 0 allocation failures, 0 Em set failures, s30 340/340 |
| STRICT + decisions, fs17nrT (T15_FS="") vs fs17crT, frame aligned | h2 Full 2,402 ticks STRICT, h2 Short 2,402 STRICT (through s30, stop tick 2400), bell Short 2,002 STRICT, door103 Short 2,002 STRICT (rooms 0101 / 0103); decisions MUST-IDENTICAL in all four (every must field ok); 0 overruns |
| TEXCHK=2 + LEON-GC (fs17cmW, Short: h2 through s30, bell fight, door103) | 3/3 TEXCHK PASS, LEON-GC PASS, pair missing 0, wrap 0; VRAM refusals 0, nocontig 0 (r100 guard=1 at Short, guard=12 at Full: the same counts with T15_FS="") |
| KOS squeeze 48 KiB at Short (twin fpfs17sqW from rP ba771dd0, IDENTITY OK; base = test 16 candidate disc with the shells) | KOS SQUEEZE GATE PASS 10/10, 0 OOM: fight min 11,672 B, call 29,480, door 14,120, leave100 11,736, leave103 11,736 (shell read in r101, and in r100 on leave100) |
| GDEMU race gate (twin fpfs17gW, gdemu profile, door103 at Short, 10 seeds) | PASS 0/10 failed, 0 bad reads; the r101 shell read at entry in 10/10 (GDEMU timing profile, emulator model, not console timing) |
| Knob-off identity (T15_FS="" rP: lane ba771dd0 vs t15/int 160802e0) | IMAGE IDENTICAL (7cce77ba), 6/6 overlays, syms identical |
| Merged tree (t15/int 9d008043 + lane d99f49e6: test 14 r101 world, cast16) | knob-off identity IMAGE IDENTICAL (18ace84b, 6/6 overlays, syms) vs t15/int 9d008043; play _end +5,056 B (8c426dd8 -> 8c428198); h2 at s30: lane Full 125,216 = Short 125,216, control 129,312 / 129,312; 0 allocation / Em set failures, s30 340/340. VRAM thrash guard at r100 Full: lane 12, control 1 (run to run: the earlier control Full run had 12); Short 1 / 1 |

Evidence: C:\Flycast-Evidence\re4-dreamcast\farshell17-20261016 (h2F-* / h2S-* W runs, strict\ summary + json,
mm-* TEXCHK runs, kos\ + kos-gate.log, gdemu\ + gdemu-gate.log, identity.txt, afterSP-fs17crW probe run).
Flycast measurements are emulator bytes and logic traces, not console timings; nothing here is a timing claim.
