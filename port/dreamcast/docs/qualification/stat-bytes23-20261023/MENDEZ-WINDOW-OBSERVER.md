# Owned Mendez window observer (host only)

Source pin: 2a14662d4b025031cd93f64eed6a5d8159d473b7. No guest was started to prepare this helper. Root owns the route fixture and actual run. Use Windows Python through existing WSL STAT slot then trace_lock.sh, with RE4DC_EMU=console, RE4DC_MAX_FLYCASTS=16, TRACE_SLOTS=16, FP_NOLIMIT=1. Preserve census-bound-run.py as the outer exact-child/deadline guard.

Argument order (all paths passed to Windows Python must be Windows paths):

    python.exe census-bound-run.py mendez-window-observer.py FP_RUN.py PPL_SYMBOL PG_SYMBOL --base BASE --cap NEW_CAP --syms "LOG HEAD STAGE" --warp WARP --pad PAD --seconds 53 --period 0 --name stat23-mendez-window

The two observer modules must remain adjacent (or on Python's module path). rT symbols verified read-only from exact existing ELF files:

| Arm | pPL | pG | logbuf | stage |
|---|---|---|---|---|
| OFF | 0x8c363a20 | 0x8c2b325c | 0x8c3e9c60 | 0x8c3f9c60 |
| ON | 0x8c3639c0 | 0x8c2b31fc | 0x8c3e9c00 | 0x8c3f9c00 |

These differ from production g ELF symbols. Root should use each arm's existing rT syms.txt for the actual three log/head/stage values. No SDK build or executable mutation is needed.

The wrapper incrementally tails complete run-output.txt lines. Only after `warp: goto 2 at room frame N` and before `warp: goto 3` does it sample actual owned-process RAM at about0.1s. A missing approach marker means no sample/no window claim. If both markers arrive in the same poll, it cannot retrospectively observe the interval. The existing top-level exact-child Popen guard remains active; the wrapper rejects a second owned guest before spawning it. It does not send controller/window/global input.

Pinned fields: include/model.h:474 pMotion+0x1d8 u32; :477 motState+0x21a u16; :489 frame+0x290 f32; :493 frameMax+0x294 u16; stat bytes+0xfc and cCoord pos+0x94. Global Status_flg[1]+0x5010 and Frame_cnt+0x51e4 are include/global.h:260/270. SceEventStart sets SF1 bit0x10000000 (src/game/sce_com.cpp:151) and SceEventEnd clears it (:194). src/game/emwindow.cpp:521-523 selects pl00537/538/536.fcv; :528 starts event; :572 sets the selected motion; :574 loops until motState mask0x4; :662 ends event. A64-byte header hash is diagnostic, not the full motion-file digest or a filename proof.

Outputs are window-ram-samples.jsonl, window-observation.json and at most3 window-stills/sXX-* directories. Stills are targeted at approach, an event-active advancing frame with the same nonempty header hash and motion pointer, and event clear. A background worker avoids blocking sampling while RGB565 is decoded. Each still stores its fresh capture-start RAM state, the triggering requested state, and whether the door marker appeared during capture. Queued captures are skipped after the door marker or owned process exit. State/VRAM are asynchronous: a requested event phase can advance before the actual framebuffer read; inspect the stored capture-start state and images.

The summary requires a sampled clear baseline, event set, motion progress with exact pointer+nonempty header hash, then event clear for normal_event_state_sequence_observed. It never automatically certifies a window jump: window_jump_certified remains false. Event flags can be shared by other scenario events, so source/fixture/still correlation remains required. Room10f or the same motion pointer alone is insufficient. At most three screenshots are taken; rejected or late snapshots are reported, not invented. Root retains all gameplay, visual and console acceptance decisions.

Controls run without any guest: pure synthetic field decoding and RAM pointer negative cases; incremental partial-line tailing, truncation rejection, incomplete event, pointer-only/missing hash negatives and a complete synthetic event sequence. All pass. Run `python.exe stat_owned_ram.py` and `python.exe test-mendez-window-observer.py` from this folder. No runtime or SDK changes.
