# Lane eng-e1p: the fourth audit's four items (2026-11-21)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1p\HANDBACK.md`. Answers HANDOVERS.md H-018.1 to
H-018.4 (fourth E1 audit, `E:\RE4DC-Lanes\audit-e1d\AUDIT-E1D.md` findings 3, 4, 6, 7, and its wording notes). Engine
numbers are **Flycast** (slots std1 and std2, function checks); PC numbers are re4ref (hostref). No timing claim; the
pacer and what the field counter counts are unchanged.

| Brief item | Result | Control and how it failed |
|---|---|---|
| 1. Camera tracks at room load (H-018.1) | every motion cut (type 6/7) of the room's camera data exported and converted when the room loads, into a room store allocated then to the bytes the tracks need (r101, the village and the fight: 11 cuts, 21,920 B; r11d, the hill: 10 cuts, 32,480 B; r119: none). A cut switch in play is a lookup (FIGHT: lookups 1, 122 moves, 0 conversions in play). A room past the store's ceiling (64 KiB, 56 cuts) is refused at load. The fight cut's 121 motion-camera ticks, and all 901 of FIGHT's camera ticks, are bit-identical to eng-e1n's n1 | CCUTCONV (`CUTCONV`: the old conversion at the cut) FAILED "camera tracks converted in play 1"; CTRKSZ (`CAMSTORE`: ceiling 1,024 B) FAILED "E1 load: camera tracks refused: room 101 needs 21920 bytes"; the old selector passed CCUTCONV (disc D) |
| 2. A refused export honoured first (H-018.2) | `CameraMotion` checks the refusal marker before it reads a header or part count, takes a lease or relocates. PC exercise `camrefuse`: oversize (7 keys), count 0, count 27, a stale valid 5-key table: the guarded buffer unchanged after the export, the construction and a move, the motion ended | control `camlate` (the marker after the reads): every case's buffer changed by the construction; camcheck's stale row FAIL as it must |
| 3. Selector (H-018.3) | every judged line matched whole against its template (fields to their own delimiters, 32-bit range); `mallinfo free` read; E1 DONE (and E1 CAMREC) against the last row plus the client's dropped rows; FIELDS counts against the rows; the schedule read to its end, a line that does not parse refuses it | CMALFREE, CTICK1, CROWTOK and the schedules PL1 / PF1 FAILED with their reasons (CONSOLE_LOOP.md section 13); each passed the old selector (disc D, PL0, PF0) |
| 4. Disc reads in play (H-018.4) | `fs_read` on `/cd` handles and the drive's read requests (`cdrom_read_sectors_ex`, `cdrom_stream_start`, `cdrom_stream_request`, `cdrom_read_toc`, `cdrom_read_sectors`) counted beside opens; a timing scene needs 0 / 0 / 0. LEON, HILL, FIGHT, BOSS: 0 / 0 / 0 (no load order change needed) | CREADX (a file opened before play, read at picture 100) FAILED "disc read in play: reads 1, sector requests 1"; COPENX still FAILED on opens; the old selector passed CREADX |
| 5. Audit notes | lanes/eng-e1o.md has the still sheet's difference list; `E1 CAMTRACK` reports part-frame decodes (was "rows"); camengine.py's docstring no longer claims the engine's lines arrive in order | - |
| 6. Flycast and docs | clean disc A2: 8 of 8 OK; stills LEON, HILL, FIGHT against eng-e1n's m2: 59 pairs, 0 moved (eng-e1j's thresholds); hill_engine, shot_engine, camengine as they must; CONSOLE_LOOP.md section 13, SERVICES.md 48d (lane eng-e1p bullet), this note | - |

## Found on the way

- The first run refused r101 and r11d for real: their tracks (21,920 and 32,480 B) did not fit the 12,288 B store sized
  for one live motion. The room store is now allocated per room at load.
- The E1 images' core camera data is the `EMPT` placeholder; read as cuts it gave garbage (r11d 23 "cuts", 13 refused).
  Room load now walks only B402..B404 blocks (the layout `calcAddr` relocates).
- The console loop client drops a report's last rows past its row budget (the fight's 900-tick report keeps rows to
  about 832); the selector's tick cross-check adds the client's closing count of dropped rows.
- Memory after play (Flycast) is lower by the room store and the heap's growth around it: LEON arena margin 450,560 B
  (eng-e1o: 495,616 B), FIGHT 237,568 B (286,720 B), HILL 114,688 B.

## Link check (final HEAD, this lane's builds)

| Image | SERVICE functions |
|---|---:|
| default | 0 (PASS, 384 allowed, 107,044 B) |
| FIGHT=1 | 114 (as before: step 3) |
| BOSS=1 | 57 (as before: step 3) |
| default SENDABLE=1 | 0 (PASS) |

## Stubs, original units, shared files, lab arms

- No stub added or removed. No original unit added.
- Shared files touched: `loader/selector.c`, `loader/cl_send.c` (one refusal mark), `core/main.cpp`, `core/frame.cpp`,
  `core/memmap.cpp`, `core/play_files.c`, `core/boot.c`, `core/e1_core.h`, `host/e1_svc_mem.cpp`, `game/Makefile`
  (wraps), `services/camera/` (camera_svc.cpp, camera_svc.h, cam_eval.cpp), `hostref/svc/` (svc4_dump.cpp, camcheck.sh,
  camengine.py's docstring), `tools/engine/build_console_disc.sh`, docs.
- Run-time controls added (boot files read before play, never defaults): CUTCONV, CAMSTORE, MEMNOFREE, TICKS1, ROWTOKEN,
  READX. PC: exercise `camrefuse`, `camroom`, control `camlate`. Disc script: scenes CCUTCONV, CTRKSZ, CMALFREE, CTICK1,
  CROWTOK, CREADX, FIGHTT; `--plan-control longcomment|fivefield`. FIGHT's NOTRACE moved to its own folder FIGHTL (root
  FIGHTL:FIGHT), as E1L and E1H.

## Not done

- No console run (the console evening). No timing claim.
- An event's camera file (a `CameraMotion` made on a file, not a cut) still converts when it is made; none runs in the E1
  scenes (0 conversions in play everywhere), and one in play is counted and fails a timing scene.
