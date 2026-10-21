# rr: the always-ready release candidate

A release should mean re-checking a finished build, not building one (user 10-19, after Test 19 took ~2 h).

## What runs

- **Watcher** (cron in WSL, every 10 min, one instance by `flock /root/rr/rr.lock`): when origin/t15/int moves,
  `rr-cycle.sh` builds the release recipe at its head and runs the QUICK tier.
- **Build:** `ch2/ch2-build.sh rP` with `recipe.conf` (T15REC from that commit + the release lane's CH2 line), then
  three `fullplay/fp_twin.sh` twins in parallel on two trees: g (full-play twin), k (KOS squeeze), c (census).
- **Package:** `test16/t16-package.sh NOZIP=1` (disc on ext4, disc_lint loader + standard, boot file check) into
  `C:\Game Dev\Emulators\RE4DC-RR\cand-<sha8>\gdemu`; a knob file is written for it in the cycle's work dir and
  compared with the newest published `test*/release-knobs.txt`.
- **QUICK tier** (Flycasts in parallel, at most 12): boot to title (release binary), h2 to the s30 movie (340/340,
  heap 4 before s30), KOS 48 KiB on the fight scene (2 runs), census of the rooms the diff touches (all 26 when
  unknown; CAST-GC, LEON-GC, TEXCHK, VRAM no-contiguous), one GDEMU race seed. missing.txt empty.
- **Report:** `C:\Game Dev\Emulators\RELEASE-READY.md`: verdict per check, heap 4 before s30, KOS min headroom,
  diff since the last good candidate, knob diff, wall time per step and per Flycast job.
- **One candidate kept:** a PASS replaces the last good one (old disc and builds deleted); a FAIL keeps it.

## Commands (coordinator)

```
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root bash /root/rr/bin/rr.sh status|cycle|full|package <tag> [N]
```

- `full`: FULL tier on the last good candidate: release checks (fp_gate.py, `release-checks.conf`), census 26 + cap
  rigs, KOS 5 scenes x 2 = 10/10, GDEMU 10 seeds, decisions pairs (h2, bell, door103, r11b; trace arms of the recipe
  vs `CH2_REF`, under trace_lock.sh slots), kit-check + kit-boot when a committed knob file names this image and
  the candidate is packaged.
- `package <tag> [N]`: GDEMU zip + Build-Assets zip of the last good candidate, knob file with that tag.
- `install` / `uninstall`: copy the tools to /root/rr/bin and add / remove the cron line.

## Safety

Reads origin only, never pushes. Own worktrees only. Skips a run when C: has under 20 GB free (`RR_FLOOR_GB`).
Deletes only its own outputs (out-rr<sha7>*, out-fprr<sha7>*, RE4DC-RR\cand-*, its evidence disc links).

## When the release recipe changes

Edit `recipe.conf` (CH2, DATA, KSETS, data dirs, CH2_REF) in the same landing, then `rr.sh install`.

## 2026-10-21 (lane rr-wire)

- Each cycle reads `recipe.conf` from the commit it builds (`git show <sha>:.../rr/recipe.conf` into `work/<id>/recipe.conf`);
  the installed copy is only the fallback.
- `rr.sh package` takes README-package.txt from the newest committed `test<N>/` (rr-newest.sh), and also writes the QA zip.
- The kit job exports `RC19D` (recipe.conf) for kit-check.sh's zipcheck.
- QA disc per candidate (standing rule 8, rr-qa.sh): the full tier builds it (QA_MENU=1 warp build of the same recipe,
  dc/qa presets, mkgdi, disc_lint, zip test) and runs QA boot keys, a QA-menu warp to r103 and a GDEMU door103 seed.
