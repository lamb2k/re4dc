# Lane eng-snd1: sound in the engine (H-025.1), finished, unaudited

Branch `lane/eng-snd1` (from `origin/engine` 2c525f3c0, `origin/engine` ba541cdcf merged). Evidence:
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
Build: lane 4a1f9adec plus the memory-map experiment (request R1, local branch `exp/eng-snd1-memmap`, not for merge).

| Scene | sound mean | sound worst | busy mean on / off | busy worst on / off | ceiling |
|---|---:|---:|---:|---:|---|
| Village (LEON) | 0.48 ms | 3.02 ms (picture 78) | 34.70 / 34.18 | 43.08 / 42.27 | FAIL (worst) |
| Hill (HILL) | 0.67 ms | 0.94 ms | 55.72 / 54.94 | 63.96 / 63.11 | holds |
| Fight (FIGHT) | 0.77 ms | 1.44 ms | 37.85 / 37.08 | 53.98 / 52.14 | holds |

The village's worst picture holds one stall of about 2.5 ms (in g1cal inside a register flush, 2,514 us; in the
mute run on plain Flycast inside a main-thread span, 2,546 us; most runs have none: h1 plain, worst 0.38 ms), cause
not found (a G2 bus wait suspected: KOS g2_lock waits for the G2 FIFO). Before the step was made atomic, KOS's
scheduler gave the main thread a whole 10 ms timeslice inside an audio step once or more a scene (10 to 20 ms worst
in every scene): fixed by running each step with interrupts off. The model cannot see: the graphics chip's fill and
sort, store-queue submission, bus contention (the G2 bus to the sound chip above all), disc timing.

## Checks and their controls
- Requests (`sndreq_check.py`, Flycast logs against `re4ref`): hill 27 of 27 PASS; village 56 of 56 same ticks, ids
  and flags, FAIL on position (requests 51-56, ticks 547-569, 1.05 to 1.38 units on the foot and body positions the
  behaviour passes; the tolerance is 1.0); shot FAIL at tick 163 (two SndStop(0) the reference does not make; the same
  with sound off, run c5shotoff: an engine-vs-reference behaviour difference, not sound). Controls drop, move, extra
  and the lab arm SNDDROP fail every scene, as they must.
- Output (`audiocheck.py` on Flycast's audio): PASS on every sound-on run (80.5% of 100 ms windows above RMS 64 on the
  final run g1cal); SNDMUTE (run g3mute): RMS 0, FAIL as it must. The image's probe: audible 0 under SNDMUTE.
- Cost ceiling (selector): SNDSLOW fails the scene (mean 8.71 ms, run c3slow on 865cdbcda; the selector check is
  unchanged since).
- Disc in play: opens 0, reads 0, sector requests 0 in every scene; all sound data read before play.

## Not done
- Disc streams are not heard (the stream player runs and ends without the disc; the AICA ring for `bgm/aica_str.dat`
  is not lifted): no scene of the engine requests a stream today (floor attributes not served, the fight's room-script
  stubs). The streaming path, its own disc reads counted per picture, is designed in SERVICES.md 49, not built.
- The village's worst picture over the 2.0 ms ceiling (one ~2.5 ms stall), not explained.
- Room changes: one room per boot; `snd_svc_room_load` reloads the room arena but the driver's `SndNextRoomInit` is
  not called (eng-load1's room change should call both).
- Door sounds (`DoorSeCall`, block 7), the room's timed sounds (`se_at.cpp`), footstep materials (`FlrAtCheck`).
- The memory map: hill and fight need request R1 (the numbers above are on the experiment branch).
