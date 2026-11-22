# Lane eng-snd1: sound in the engine (H-025.1), finished, unaudited

Branch `lane/eng-snd1` (from `origin/engine` 2c525f3c0, `origin/engine` cd8b8762b merged). Evidence:
`E:\RE4DC-Lanes\eng-snd1` (HANDBACK.md, STATUS.md, REQUESTS.md, runs/, ref/). Design and checks: SERVICES.md section 49.

## What was built
- `engine/services/sound/aica.cpp`: the old port's AICA backend lifted and adapted (banks in a fixed AICA layout, AX
  voices on AICA channels, a minimal GM synth for the BGM sequencer, the register flush), no old-port globals or hooks.
- `engine/services/sound/snd_host.cpp`: what the hosted driver needs below it (interrupt guards, ARAM addresses, the
  stream player's I/O without the disc, the driver's own generator `snd_rnd`, logged weak stubs).
- `engine/services/sound/snd_svc.cpp`: boot (the four sound system files, `SndDriverInit`), the room's sound banks
  loaded with the room (part by part as `dvd.cpp` does, only the converted images), the room's STB and BGM start, the
  tick's `SndWatcher`, the 5 ms audio frame on its own thread with each step atomic (interrupts off), the request log,
  the cost per picture, the output probe, the report lines, the lab arms SNDOFF / SNDMUTE / SNDSLOW / SNDDROP.
- The original driver (`src/game/snd*.cpp`, 22 units) hosted unchanged; `allowed_original.txt` group
  `sound-driver-waived-H-025.1`; `game/sound.mk` (one include line in `game/Makefile`); `host/e1_stubs.cpp` lost its
  SndCall / SndStop stubs; `loader/selector.c` prints the sound line and fails a timing scene over 1.0 ms mean or 2.0 ms
  worst (or with no sound line); `hostref/host_stubs.cpp` logs the reference's requests.
- Tools: `services/sound/tools/sndreq_check.py` (requests against the PC reference, controls drop / move / extra),
  `audiocheck.py` (Flycast's own audio output, SDL disk driver).

## Numbers (MODELLED (console-build dynarec at 70 MHz, calibrated on the old port); pictures 41-640)
Build: lane a7aa905a4 (memory map R1 in), run k6cal (slot fly2); the off arm ASNDOFF and the older off run g2off.

| Scene | sound mean | sound worst | busy mean on / off | busy worst on / off | ceiling |
|---|---:|---:|---:|---:|---|
| Village (LEON) | 0.48 ms | 0.69 ms | 35.26 / 34.72 | 43.49 / 42.83 | holds |
| Hill (HILL) | 0.68 ms | 0.90 ms | 56.30 / 54.94 (g2off) | 64.62 / 63.11 (g2off) | holds |
| Fight (FIGHT) | 0.75 ms | 1.66 ms | 37.77 / 37.08 (g2off) | 53.14 / 52.14 (g2off) | holds |
| Boss (BOSS, headless) | 0.59 ms | 0.82 ms | 10.24 | 18.78 | holds |

A sound step or call of about 2,500 us lands in some runs (village run g1cal, hill run k1cal), always on a whole
emulated second: KOS's microsecond clock jumps 2.5 ms forward once a second (found by lane eng-skel1), not sound work;
the worst ceiling is judged with the clock fixed (integrator ruling; lane eng-clock1). Before the step was made
atomic, KOS's scheduler gave the main thread a whole 10 ms timeslice inside an audio step (fixed by running each step
with interrupts off). The model cannot see: the graphics chip's fill and sort, store-queue submission, bus contention
(the G2 bus to the sound chip above all), disc timing.

Memory after play with sound (k6cal): margin to the behaviour arena / arena peak: village 572 KB / 166 KB, hill
272 KB / 294 KB, fight 152 KB / 825 KB of 1 MB, boss 2,196 KB / 454 KB. Nothing hangs.

## Checks and their controls
- Requests (`sndreq_check.py`, run k7fun against `re4ref` rebuilt after the eng-fix1 merge, lane 28475242a): village 56
  of 56, hill 27 of 27, shot 30 of 30 PASS, positions included. The village failed on six footstep positions (ticks
  547-569, 1.05 to 1.38 units) until request R9: the engine's village started the behaviour generator at 0 while re4ref
  seeds the fixture's 0x0d37 (`core/partner.cpp` seeded the hill only), so the aim sway drew other numbers from tick 393
  and Leon's yaw was 0.052 degrees off from tick 485. The seed is now part of each scene's start state (`core/route.cpp`,
  set in `core/main.cpp` room_init where re4ref sets it); the village is bit-identical to re4ref over 641 ticks. What
  moved in the village with the fix: the camera and the parts' matrices from tick 393 (the aim), Leon's yaw from 485,
  his position from 487, sound request positions from 493; the hill and the shot did not move. Controls drop, move,
  extra, the control scene CSNDDROP, and CSEED0 (the seed left at 0: the footsteps fail again) fail, as they must.
- Output (`audiocheck.py` on Flycast's audio): PASS on the final run k6cal (62.0% of 100 ms windows above RMS 64);
  CSNDMUTE (run k6mute): RMS 0, FAIL as it must; the image's probe reads audible 0 under it.
- Cost ceiling (selector): CSNDSLOW fails the scene (mean 6.24, worst 10.60 ms, run k6cal on the final build).
- Disc in play: opens 0, reads 0, sector requests 0 in every scene; all sound data read before play. The disc script
  stages the sound files from the game tree (R4).

## Not done
- Disc streams are not heard (the stream player runs and ends without the disc; the AICA ring for `bgm/aica_str.dat`
  is not lifted): no scene of the engine requests a stream today (floor attributes not served, the fight's room-script
  stubs). The streaming path, its own disc reads counted per picture, is designed in SERVICES.md 49, not built.
- Room changes: one room per boot; `snd_svc_room_load` reloads the room arena but the driver's `SndNextRoomInit` is
  not called (eng-load1's room change should call both).
- Door sounds (`DoorSeCall`, block 7), the room's timed sounds (`se_at.cpp`), footstep materials (`FlrAtCheck`).
- The village's cost re-run once the clock fix (eng-clock1) is in `engine`.
- The corrections the eng-fix1 table gives to sound (`SND_WALL_ALT`, `RADIO_SUB_RT`): not built.
