# Qualification preflight for SDO3

`prepare_qualification.py` is read-only except for an optional small, exclusively
created JSON plan. It verifies the four frozen alternate hashes, their unchanged
base-package sizes/source CRCs, the exact clean source HEAD, recipe DATA and the
existing tool/fixture paths. It does not build, stage data, create media or launch
Flycast. Source/runtime files remain frozen at e66ec61e4.

Run from WSL with the main lane's integration checkout and full40-character SHA:

```text
python3 /root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/prepare_qualification.py \
  --tree <main integration tree> --source <full integration SHA> \
  --alternates /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023 \
  --work /root/work/lanes/dedup-offline23-scratch/qualification \
  --off-label <unique built Off label> --on-label <unique built On label> \
  --off-out /root/probe/lanes/route/out-<Off label> \
  --on-out /root/probe/lanes/route/out-<On label> \
  --output /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/qualification-plan.json
```

The output directory must already exist, and the plan file must not exist.
`--off-out` and `--on-out` may be omitted while programs are still building; the
plan then says PENDING and claims no program pin. Supplied outputs require an
exact one-line source SHA in stack.txt, a resolved SCENERY_DEDUP0/3 value and
empty missing.txt. ELF/candidate/stack/resolved-knobs/syms files are pinned, but
those hashes alone never establish image identity or a runtime gate.

The plan contains exact `t11-fix.py --set` argument arrays for both arm labels and
separate `PKG_K` paths for t8-pkgtree. Apply the same four alternates to both arms;
standard ps2-world filenames remain in both data trees. This keeps alternate data
and disc layout equal while knob0 ignores the alternate filenames. Keep the exact
recipe's literal exported dataset paths are included in each stage environment;
nonliteral shell expansions are refused rather than evaluated.
No DATA registration, production recipe, watcher, release or SD change is needed.

The gate plan reuses existing tools directly:

- Knob0 image: remove .stack with the target objcopy and compare the program SHA
  with the same-recipe pre-change control; ordinary ELF hashes do not prove this.
- KOS: the existing squeeze twin needs KOS_WATCH1/KOS_SQUEEZE1/W11_FIXTURE1. Run
 49152 bytes as one block and as fragments. Fight/call/leave100/leave103 runs are
 60 seconds; hold/endpoints/zero fault lines/headroom>=4096 must all pass.
- s30: require340/340 and heap_before at least the matched Off arm. The existing
 rr h2 run is300 seconds, and its named full gate allows420; neither is silently
 scheduled here. Under the requested60-second cap, main must select a qualified
 bounded s30 fixture or deliberately use the already authorized named exception.
 A60-second timeout that misses s30 is INCOMPLETE, never a passing gate.
- Census: use the existing r100/r101/r103 CAST-GC fixtures and a properly pinned
 census twin with TEX_CHECK/MCHECK_LEONGC/NATIVE_MODEL_REGISTRY_CENSUS and VRAM_ROOM_LOG enabled. Require0 texture failures,
 no-contiguous/refusal/reread counts0 and unlisted CAST-GC/LEON-GC0. Verify live
 characters are drawn and On logs show the expected SDO3 package adoption.
- Look: existing still-r101/still-r103 fixtures freeze at room frame700. Use
 fp_run.py with --seconds60 --period5. Only compare shared captures after both
 logs establish the same freeze. Existing pix.py expects cross-k/cross-p and
 farm-k/farm-p folders; define k=Off and p=On. Earlier moving captures are not
 a matched rendering result.
- GDEMU: use the existing door103 fixture, console proxy, GDEMU profile and seeds
 1..10. MAXP1 and SECS60 keep runs bounded. Every seed must reach r103 with no
 bad reads or stop faults. These are proxy correctness checks, not console speed.

Every actual guest job runs under the existing WSL trace_lock.sh, no more than3
Flycasts in this lane, with no global input. Main owns execution and scheduling.
The preflight does not generate executable job lists or touch the live rr watcher.

The `qa.arms` plan lists the existing primitives for future private Off/On discs:
unique ch2 label prefixes, explicit QA_MENU1 and knob0/3 builds, exact four-file
staging, t8-pkgtree, stage_route/mkqa presets, standard-layout mkgdi and both loader
and standard disc_lint checks. QA programs/disc hashes remain PENDING. Copy the
listed preset directory into that arm's dc/qa before mastering and preserve
README/program/data/source pins with each private package after safety gates.
Unmodified rr-qa.sh hardcodes rr<sha7>qrW, and rr-cycle/rr-jobs assume shared rr
labels; invoking them for these custom same-source arms would risk output reuse.
## Existing bounded s30 fragment

The optional `--s30-fixture` pins this existing file without copying or editing it:

```text
/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/native-memory813/fixtures/s30-only.txt
```

Source:222 bytes, SHA2569883b78b34beed91ea6fe03a19e3e79cbb5e903dd173d1fb13c83a2e9534d110.
The stock runner removes only CR bytes:221-byte wire SHA256a5dc391e780a97f6759f223753f2caeabd90eec55e5853514d0f9d054d3d1d36.
It declares a post-ambush r100 start, RSF3/10/13 and scenario0x10, then presses A at
room frame60 to invoke the original area callback. It does not force movie
completion, alter required movie frames or bypass the movie's own loan/return.

Its actual source2158baff console-proxy run is preserved at:

```text
C:/Flycast-Evidence/re4-dreamcast/pvs23-20261022/scratch-memory2158-2158baff82e0812e5cf9ed3186e27e22d753d045-s30-only-01/
```

The captured run-result.json sets seconds54, goal at34.9s and elapsed37.0s;
controller-result.json records actual root37.270s and closure37.296s. The log and
memory-result.json show MOVIEARENA borrow token1, return restored1,340/340 frames
uploaded/presented, full movie11.922s, heap_before163328 and resumed world draw.
This demonstrates how the original complete movie fits a one-minute fragment:
it starts after the earlier house/ambush movies and their waiting actions.
No historical symbol addresses or acceptance results transfer to a new candidate.

Use the current main arm's own base, symbol triple and new evidence path with the
plan's seconds54/stop-retired/grace2 arguments, console proxy and trace lock. It
still needs a new Off/On result. Timeout is INCOMPLETE. On must show fresh SDO3
adoption after reload and world rendering resumption, with the current source/data
pins. This checks the declared-state movie/heap/loan/reload fragment only. It does
not reproduce full H2's tight94KB heap state or satisfy that full route gate.

The later Claude world-scratch23 h2C pass used a300-second cap and168.8 seconds
elapsed; fix-r200-gears23 h2 similarly took168.3 seconds. Neither is one-minute
proof. Keep the full H2 floor requirement pending under a60-second-only contract;
never substitute the higher163328-byte fragment heap or extend a timeout silently.

## Evidence auditor

`audit_evidence.py` only reads explicit files and writes a new JSON receipt. It
never stages, builds, launches a guest or compares screenshot pixels. Give it an
existing preflight plan containing the five programme file pins, or a smaller
JSON with `arms.on.program.files` / `arms.off.program.files` using the same
`{path, bytes, sha256}` entries. Each arm needs re4dc-game.elf, candidate.txt,
stack.txt, resolved-knobs.txt and syms.txt. The actual resolved SCENERY_DEDUP must
match the selected arm. Preserve the plan and its source revision separately.

Example from WSL, using the completed console On s30 capture:

```sh
python3 port/dreamcast/tools/d367/dedup_offline23/audit_evidence.py \
  --capture /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/s30-on-console-r2 \
  --program-plan /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/programme-pins-af09-offon-r2.json \
  --arm on \
  --fixture '/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/native-memory813/fixtures/s30-only.txt' \
  --fixture-sha256 9883b78b34beed91ea6fe03a19e3e79cbb5e903dd173d1fb13c83a2e9534d110 \
  --base-json /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/base-on/base.json \
  --track-sha256 d1ba7ae9754e12d1ae45c72d41f6a518ce48df8514451435bb0d6658c12e7eef \
  --output /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/my-new-audit.json
```

Windows paths are also accepted. Output creation is exclusive: use a new filename
for each revision, preserving earlier reports. The literal historical r1 capture
is `C:/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023$CASE-on-r1`; quote it
with single quotes in shells so `$CASE` is preserved. That run reports
`emu=harness`. It cannot establish console-proxy acceptance. The default expected
emulator is `console`; a mismatch is explicitly reported as a warning.

The receipt hashes the auditor, plan, five current programme files, source/wire
fixture, captured fixture, run-result/log and every image in that capture's
`shots/` directory. It does not search other capture directories. Base JSON checks
bind the capture's disc path to the named base directory and its ELF path to the
verified programme. The explicit track SHA is checked against run-result's
reported track hash. These are metadata bindings; this auditor does not read back
the disc bytes or certify what the emulator executed.

Movie observations retain numbered raw rows and terminal frame/upload/present
counts, heap_before/heap_active, movie/media durations, matched borrow/return token,
restored flag, SCNDEDUP3 rows during the loan and cadence. Equal340 counts describe
what the log reports; the auditor does not upgrade them into a complete route
pass. KOS observations include exact held amounts and minimum headroom/top block.
They do not decide whether every required scene endpoint was reached.

Diagnostics have separate `FLAG_ABSENT`, `NOT_INSTRUMENTED`,
`INSTRUMENTED_NO_TELEMETRY`, `INSTRUMENTED_OBSERVATIONS_ONLY`, or
`UNVERIFIED_PROGRAMME` states. TEX_CHECK controls TEXCHK, MCHECK_LEONGC controls
Leon-GC, and **NATIVE_MODEL_REGISTRY_CENSUS controls CAST-GC census**. VRAM_ROOM_LOG
and KOS_WATCH/KOS_SQUEEZE are tracked separately. Zero ordinary VRAM counters or
absent texture/GC rows do not substitute for a pinned diagnostic twin. The auditor
retains NMRS/context/alivelist rows and fallback candidates; run the existing
cast_gc.py with the correct not-drawn source allowlists for the official check.
Zero fault counters and crash-screen readiness are separated from actual fault
candidates. Missing fault text remains an observation, not a passing gate.

Every `gate_verdict` is `NOT_EVALUATED`. Exit0 means the requested file/fixture pins
matched; it does not mean emulator mode, RUN_COMPLETE, diagnostics or safety gates
passed. Exit1 indicates pin/identity mismatches; malformed or unavailable required
inputs also stop the script. Main owns gate decisions and must inspect warnings,
run-result errors/status, telemetry and coverage. Screenshot inventory proves
file identity only. Arbitrary wall-time shots do not prove matched-frame pixels.

The authored smoke receipts use programmes from integration
af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34. Both completed console s30 r2 logs report
340/340 uploaded/presented, restored1 and heap_before140448; On reports fresh SDO3
adoption during the loan. This remains the declared-state fragment, with full H2
heap-floor coverage pending. Ordinary programmes have texture/census/KOS checks
disabled. No physical-console timing or pixel-identity claim follows.
