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
recipe's RC19D and other exported dataset paths when executing the printed arrays.
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
 census twin with TEX_CHECK/MCHECK_LEONGC enabled. Require0 texture failures,
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