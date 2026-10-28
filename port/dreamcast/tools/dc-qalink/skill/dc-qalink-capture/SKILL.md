---
name: dc-qalink-capture
description: Measure a KallistiOS Dreamcast program on real hardware through the dc-qalink relay - dial, labelled capture start/stop, session scripts, reading the summaries, and A/B comparisons at the same spot via GOTO presets. Use when asked to capture, benchmark, compare builds or collect telemetry from a Dreamcast over the modem link.
---

# Capture sessions with dc-qalink

Tool: `pc/dc_qalink.py` (`--ssh dreampi`, or `--relay host:port` through a tunnel). README: wire format and limits.

1. **Link up:** the console's status line shows UP (dial from its menu, or it auto-dials).
   `dc_qalink.py --ssh dreampi send PING` must answer `OK PONG` before anything else.
2. **Same spot every time:** `send GOTO <preset>` (list with `send PRESETS`), then `wait 3` so loading settles.
3. **Capture:** `capture start <label>` ... play or `wait <s>` ... `capture stop`. Output:
   `captures/<label>.log` (the raw section) and `<label>.summary.txt` (each numeric `row.key` averaged, with n).
   Labels must be unique per session (`fight-a`, `fight-b`).
4. **Session scripts** (one action per line, `#` comments; any line that isn't `wait`/`capture` is a command):
   ```
   GOTO level1-boss
   wait 3
   capture start boss-a
   wait 30
   capture stop
   ```
   Run: `dc_qalink.py --ssh dreampi session boss.txt` (stops at the first failure; `--keep-going` to continue).
5. **A/B:** run the same script on build A and build B (different labels), then compare the two summary files
   key by key. Quote: label, build, preset, seconds (`telemetry rows: N`), and the mean of each key. Treat a
   difference smaller than the run-to-run spread of two A captures as noise.

## Reading results

- `telemetry rows` is seconds of data; fewer than expected means rows were skipped (see `link.skips` /
  `send STATUS`: `skips`, `rxdrop`, `stall`).
- A capture still cuts if one marker datagram was lost: any echo counts (relay `C`, console `M`, `A` or its
  `dcql-mark:` log line). An empty section means both markers' echoes are missing: repeat it.
- Numbers are console measurements only when the run was on hardware; label Flycast runs as Flycast.
