# Local bounded MODELLED qualification helpers

These helpers belong to the private October 27 r101 experiment. They contain no
game data and change no runtime source or production recipe. Their private
paths identify this experiment; they are not a portable public build workflow.

- `derive-frame27.py` derives `GlobalWork::Frame_cnt` from the exact ELF's DWARF
  and `_Global` symbol, rather than assuming a PC sampler or a source offset.
- `prepare-model27.py` verifies all 1,653 pinned release files, creates an owned
  hard-link clone and unlinks each replacement before writing. It permits only
  the matched programme/overlays, fixture, and candidate mesh/strip-group pair.
- `master-model27.py` masters through `model-mkdisc27.sh` and verifies every
  on-disc file with the existing independent ISO reader. Raw ELF programme,
  scrambled on-disc programme and generated CD-R boot IP have separate hashes.
- `model-mkdisc27.sh` follows the existing single-track MODE1/2048 CD-R contract.
  Its fallback also handles KOS elf2bin returning success with no output. It
  refuses existing outputs and optional fixture copies over hard-linked data.
- `snapshot-model27.py` reads this run's exact recorded process, checks the
  executable path and records source ticks before/after a full RAM snapshot.
  It never pauses, writes to, or extends the guest. It is run concurrently with
  an already authorized bounded run; its timeout does not prolong that run.
- `report-model27.py` preserves the distinction between CPU-work estimates,
  partial contextual attribution and validated disjoint world lower bounds.
  It uses the existing local logic18 contextual exporter outputs and benchmark
  classifier; no inclusive timing rows are added.

Measured stack: `ad812407345df19d3d39866420cc2235d9aa4b0b`, current release
recipe, `WORLD_REBUILD27=1`, `PACE_MODE=off`, cap 4, `PC_SAMPLER=0`,
`WORLD_CENSUS24=0`, `WORLD_METER=0`, `GAME_PWC_DIAG=0`, `QA_MENU=0`.
ELF SHA256: `9b669d1e6ab7a568fae586836bae52254ee0692344a4c8eca8c05e29b0c58a30`.

Evidence is local under
`C:/Flycast-Evidence/re4-dreamcast/world-rebuild27-20261027/`:
`MODELLED-RESULTS-v1.json`, `MODELLED-RESULTS-v1.md` and the three
`hwmodel-v1-{A,B1,C4}-cross` directories. Each guest completed within 55 seconds.
Thirty counted source ticks (300--329) contain 30 Render and 90 world mesh
entries. Only ticks 300 and 329 have timing traces, each with one Render and
three mesh passes. The two traces are two timed drawn worlds, not thirty.

The validated disjoint world lower bounds are A 5.528, B1 3.361 and C4 4.369 ms
per observed drawn world. They already reject the 2 ms target for B1 in this
test. Complete total-world timing remains unqualified because contextual root
coverage is partial. This is MODELLED CPU evidence; it does not qualify cache
Flycast/GDEMU transport, PVR deadlines, appearance, the route or console timing.

## B1 live-mask follow-up

`preflight-live-mask27.py` verifies the supplied new programme and derives its
own frame address before a single authorized follow-up capture.
`report-live-mask27.py` compares that capture with retained B1 OFF evidence,
validates the unchanged B1 assets/fixture and counts actual draw entries from
the new ELF's exact symbols. It includes programme layout changes in the result.

The one ON capture uses ELF
`ad21da2dff7650d1b13b875cbb9c14752f5325245989859c010568cf8a9af98d`,
physical Frame_cnt `0c379f80`, source supplied by main at `3b29ffab3`.
It completed in 42.424 seconds with the same two timed ticks and 30-counted-tick
window. Estimated CPU work is 21.038 -> 19.613 ms/drawn world. Validated partial
world cost remains at least 3.135 ms/drawn world, so total-world <=2 ms remains
unqualified. Different contextual coverage prevents interpreting its lower-bound
delta as total-world savings. `_end` grows 32 bytes. Exact model output parity,
unchanged B1 game data and the draw denominator are recorded in
`MODELLED-LIVE-MASK-v1.json` and its Markdown companion in the same evidence root.
Only ON was freshly run; OFF remains the original retained evidence.