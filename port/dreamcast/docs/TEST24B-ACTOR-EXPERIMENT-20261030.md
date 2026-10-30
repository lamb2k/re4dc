# Test24b incremental actor experiment, 2026-10-30

Status: target-build and disc-file checks passed. Both QA discs are prepared;
Flycast boot, console timing, visual and route acceptance are pending. No FPS
gain has been measured for this pair. This branch does not change the release.

## Scope and hypothesis

Start at frozen Test24b `92cec32fa60ef73e0508e7eba2c8b59113225d2f`.
The experiment's code is `df9b35961c04a7472fb72c39f17eacde6262cea2`.
Keep the frozen Test24b contributor assets and QA disc contents.

Enable the existing `ACTOR_SETUP_LEAN` and `ACTOR_BYTES_LEAN` implementations
as the first family drawn from the K45 configuration. Both are already in
Test24b, off in its recipe. No later renderer source or replacement assets are
imported. Setup reuse retains kernel arguments/dispatch within the current
model part; byte reuse avoids rewriting constant ARGB while updating positions
and UVs. Per-vertex-color and incompatible MOVCA paths retain their fallbacks.
The configuration keeps `ACTOR_VTX_KERNEL=1`, `ACTOR_NO_CLEAR=1`, and
`ACTOR_MOVCA=0`. Live eligible coverage and net benefit still need measurement.

The only source additions are the QA-link/remote-control closure and a bounded
cost observer: original QA link `ae0f7b2b`, scoped console fixes `7acd7d8f`,
and scoped driving controls `e6f69b9c`. QA_LINK stays default 0. The Pi service
and protocol are not upgraded by this experiment. The later bench profile and
ALL ON renderer stack are excluded.

## Build arms

Use the published Test24b Build-Assets kit and its frozen knob file from
`4afac324:port/dreamcast/tools/d367/test24b/release-knobs.txt`. Pass it explicitly
through RELEASE_KNOBS; this historical checkout's default points to Test24.
Use a fresh OUT and OBJDIR for every arm and build serially on a case-sensitive
Linux filesystem. Follow the repository's contributor toolchain instructions.

Common diagnostic arguments:

```text
QA_MENU=1 WARP_AFTER_RESET=1 DBG_WARP=1 PC_SAMPLER=1
GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 PACE_COST_LOG=1
QA_SRC=df9b3596
```

| Arm | QA_LINK | ACTOR_SETUP_LEAN | ACTOR_BYTES_LEAN | QA_TEST |
|---|---:|---:|---:|---|
| No-link diagnostic control | 0 | 0 | 0 | 24BBASE |
| Linked control | 1 | 0 | 0 | 24BBASE |
| Linked actor candidate | 1 | 1 | 1 | 24BACTR |

The release-identity arm instead uses QA_MENU=0 QA_LINK=0 PACE_COST_LOG=0
ACTOR_SETUP_LEAN=0 ACTOR_BYTES_LEAN=0, with the published recipe.

Build with `port/dreamcast/build-public.sh <arm arguments>`. Preserve its
resolved-knobs, compile log, ELF, all overlays, and an empty missing.txt receipt.
Stage each linked arm using `tools/swap-program.py` with the frozen Test24b QA
GDEMU zip and that arm's whole output directory. An ELF without its matching
overlays is not a valid image. Run both standard and loader `disc_lint.py`
profiles with full scan. These are data/layout checks, not boot acceptance.

## Verified preparation

All four fresh full-recipe target builds passed; missing.txt was present and
empty for each. The release-identity raw program matches the published SHA256
`a6fb054914ccebc64beeca287b2b6b47f397b87d38304c3e7553dde1e8d54b53`;
all 15 overlays also match the retained published release build.

After normalizing only output paths, the paired resolved settings differ in
the two actor flags and QA_TEST/QA_NAME. Actual preprocessing confirms the
reuse code absent in control and present in candidate. Of 613 objects stripped
of debug information, only native_actor_fast.o and qa_menu.o differ. The short
cost observer is absent from the release program and present in diagnostic arms.

Both discs pass standard/loader full-scan lint and file readback. Exactly the
program plus 15 overlays change. All 1,646 remaining file payloads are identical
to the frozen QA disc, including its world, characters, textures, audio and movies.
Low-density tracks and disc.gdi are unchanged.

| Arm | Raw program SHA256 | track03 SHA256 |
|---|---|---|
| 24BBASE | 62c97a5547704dd6c0576849bc23930e33273bc53ff059c4efa87ab3d468f70b | 60852db705ded8eb029ad67c85229f7c04f1ed125199f9023d41fb5230d4c3a3 |
| 24BACTR | 4186c3a7a12b072f6bfd16e28a1312a47112d9ad2fe2226f5b423509ac957781 | d642c238deee409bd16ca828f1716ea333da03791575c4984bae284a40c85f95 |

## Measurement contract

`PACE_COST_LOG=1` requires PACE_VMU=1. Once per VMU reporting window it emits:

```text
PCOST f=<frame> vb=<fields> dn=<drawn ticks> dus=<drawn cost sum us> sn=<skipped ticks> sus=<skipped cost sum us>
```

These are integer sums of the existing pace-end cost, classified by the current
tick's skip flag. They are not exponential averages. Drawn cost is dus/dn,
skipped cost sus/sn, and whole-tick cost (dus+sus)/(dn+sn), when denominators
are nonzero. The initialization tick establishes the window start and is not in
the cost sums; discard the first reported window when aligning other counters.
A drawn tick count is not a GPU completion count. Window fields measure elapsed
time, not CPU work.
Emission happens after the measured endpoint; link/logger interrupts and other
observer overhead are not proven zero. Keep observers identical for A/B/A and
use the no-link arm if the observer itself needs isolation. Reject incomplete
or dropped log windows; do not silently treat missing samples as zero.

On the console, verify the PING build label/source before each capture. Use
control -> candidate -> control at the same r100 position, camera, enemy count,
pacing mode and route state. Warm up consistently, separate loading/cutscene
windows from steady play, and retain whole-run stalls as a separate result.
Record 120 seconds per comparable location/encounter, including FPS, game speed,
drawn/skipped cost, phase costs, GPU completion/wait, memory, disc reads and audio.
Check tree explosives/other previously missing assets and the ambush explicitly.

Do not enable the family in the release until repeated console samples show a
net whole-frame gain with unchanged gameplay and an acceptable look. Stalls,
audio dropouts and missing assets remain correctness gates, even if FPS improves.
Larger logic/effect and data-residency families require their own dependency and
measurement gates. K45 sensitivity estimates are not measured Test24b savings.
