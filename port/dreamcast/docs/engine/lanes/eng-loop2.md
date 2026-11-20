# eng-loop2 hand-back (step 1 preparation: the loader's Flycast proof and one console disc), 2026-11-20

Lane `eng-loop2` on `lane/eng-loop2` from `origin/engine` 98aced1dc. Status: **finished, unaudited**. Kind:
emulator. Every number here is **Flycast** (console-like build, GDEMU disc profile, dynarec on for the console disc);
none is a result, the console decides. Evidence: `E:\RE4DC-Lanes\eng-loop2\evidence`. Design and results:
[CONSOLE_LOOP.md](../CONSOLE_LOOP.md) sections 8 and 10.

## 1. Loader checks (console-like Flycast)

| Check | Result | Control |
|---|---|---|
| Loader reaches `WAITING FOR THE PC`, `status` sees `HELLO` | pass | - |
| `run testprog --args report` | pass: `DONE`, report CRC ok | - |
| `--corrupt payload` / `--corrupt stream` | refused before running (`VERDICT sha256` / `stream crc`) | they are the controls |
| crash / hang with a 20 s deadline / return | `CRASHED` (event 180) / `TIMEOUT` / `DONE` exit 0, loader waiting again | each other's control |
| Sender killed and restarted | resumes (first ack at chunk 68 of 128) | a different stream starts over (first ack at 0) |
| Host tests after the hand-off header change | 16 / 16 | section 7 of CONSOLE_LOOP.md |
| Bench and E1 images sent through the loop | both run, reports back (2 windows; 640 rows) | - |

Fixes: the release game's KOS disc fixes linked into the loop's programs (`kosfix.mk`; without them the console-like
Flycast stops a program that reads the disc after the loader's jump); the test program's crash falls through to an
illegal instruction (Flycast does not fault on a misaligned write); the client's watchdog sleeps once to the
deadline.

## 2. The one console disc

- Script `port/dreamcast/tools/engine/build_console_disc.sh` (WSL): clean checkout of a commit (default
  `origin/engine`), builds the selector and the four engine images with `SENDABLE=1`, stages the private packs (paths
  overridable; defaults are the files the earlier lanes' discs carried, checked by hash), writes the GDEMU disc,
  `SHA256SUMS`, `MANIFEST.txt`, `SCENES.TXT`, the ELFs and `KEEP`.
- Scenes, one boot, in order: bench (village cross, hay-fork view, arms a and b A/B/A, control window), Leon in the
  village, Leon and Ashley on the hill, the four-Ganado fight, El Gigante on the bench, El Gigante hosted.
- Selector `engine/loader/selector.c`; send-able build option `engine/loader/sendable.mk` + `cl_send.c`.
- Flycast proof (one boot, all six scenes, the summary screen): bench, Leon, hill, fight and El Gigante hosted OK;
  **El Gigante on the bench FAILED**: the engine's bench refuses lane eng-boss's pack at pack-loader stage 5 (the
  recorded-input checks), so it needs a re-bake with the current packer. Controls: a dropped pack with the
  selector's check (FIGHT "missing FIGHT/CROSS.PAK") and without it (BENCH "M1 native pack REFUSED"; LEON
  "E1 load: missing /cd/st1/r101.arc") are FAILED in the summary, never skipped.
- The E1 images print a `fields` column but never fill it: the floor's presented-interval row is not measured for
  Leon, the hill, the fight or the boss. The summary says so instead of showing 0.

## 3. Shared files touched

- `port/dreamcast/engine/bench/Makefile`: one block (`ifeq ($(SENDABLE),1) include ../loader/sendable.mk`) and
  `$(CL_SEND_OBJS)` / `$(CL_SEND_LDFLAGS)` on the `native.elf` rule.
- `port/dreamcast/engine/game/Makefile`: the same block and the same two additions on the `e1.elf` rule.
- `.gitignore`: the lane's private staging and build folders.
- Everything else is in the lane's own folders (`engine/loader/`, `tools/consoleloop/`, `tools/engine/`, this file,
  CONSOLE_LOOP.md).

## 4. Not done

- El Gigante on the bench: no re-bake of its pack (outside the lane).
- Presented fields in the E1 images: not added (engine `core/`).
- No console run; no disc on the SD card.
- The loader's GDEMU disc was not re-staged with this lane's changes (the evening does not use the loader).
- The console-like Flycast build writes nothing to its captured stdout: the serial line was checked in the standard
  Flycast slot.
- The `SENDABLE` images copy their own text lines into the report inside `printf`; where an image prints during its
  timed pictures this costs a little. Not measured.
