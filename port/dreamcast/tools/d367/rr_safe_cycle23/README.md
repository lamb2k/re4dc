# RR bounded console adapter (source checkpoint; not a completed RR cycle)

Source baseline: `fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2`.
New observation profile: `RR_FINAL_GDI_BOOT45_CHILD55_LIMITED_V2`.
This deliberately differs from the installed 60/300-second harness profile.
Installed cron's `1023-2350-fb254e82` captures remain legacy evidence. Its H2
RUN_COMPLETE at 167.7 seconds with `emu=harness` cannot establish this profile.

Successor to frozen2c6c62: only a newly owned capture emu.cfg is canonicalized
to explicit aica.LimitFPS=yes immediately before guest Popen. Original template
bytes remain unchanged; pre-limit cfg and before/after SHA are retained. Wrong,
duplicate, malformed, foreign-section or non-template config content refuses.

The source helper can prepare an isolated, hash-inventoried RR/reader capsule.
Its only admitted execution entry is **one explicitly reviewed final-GDI boot**.
There is no automatic quick/QA cycle entry, SDK build, mastering, cleanup,
installed-script modification, cache eviction, checkout, metadata promotion,
cron creation, or RELEASE-READY update. It refuses the whole-cycle phase.
This is intentional: the minimal remaining cycle patches are listed below,
so root can review concrete changes before enabling a successor.

## What is implemented

* Installed RR scripts and recipe are saved byte-for-byte as non-executable
  `.REFERENCE` files. The dangerous installed `rr-cycle.sh` cannot be invoked
  through the entry. Source preparation itself does not acquire a guest/build
  slot or start anything.
* The current-head reader and exact tracked segment fixtures are copied into a
  private `fullplay`. Its new `fp_run.py` wrapper always takes the root shared
  three-guest slot, then a canonical 16-way trace slot, then runs the guard.
  Both unchanged nested call structures use that private wrapper: KOS's
  `dirname($0)/fp_run.py` and GDEMU's `cygpath(dirname($0)/fp_run.py)`.
  Actual nested shell bodies are exercised by host-only recorder controls.
* Private `rr-jobs.sh` retains quick/QA selection, census selection and all
  conditions, clamps requested observation windows to 53 (boot stays 45),
  refuses full tier, and points FPD to the private directory. KOS's five scene
  durations and GD's duration become 53; GD cannot accept a longer SECS override.
  The retained KOS shell still declares its historical unthrottled setting;
  actual V2 execution refuses FP_NOLIMIT other than0, so a future complete-cycle
  successor must explicitly review its limited KOS profile. KOS levels, endpoints, 4096-byte headroom requirement, all OOM/bad-read checks,
  GD seeds, H2 movie/frame requirements and QA boot/warp conditions are retained.
  A gate that cannot finish in 53 seconds **fails**. Nothing is removed to fit.
* `hold` takes the actual installed `/root/rr/rr.lock` nonblocking regardless of
  inherited `RR_LOCKED`. It does not run while cron owns that lock. Child routes
  verify the actual `/proc/locks` holder, PID start time, descriptor inode and
  configuration SHA; this is repeated after waiting for guest/trace slots.
  Root's lease file is exclusive and retained. A stale lease refuses reuse.
* Root must bind the exact current programme, all 14 modules, assets/disc,
  fixtures, symbols and closure receipt in an explicit reviewed configuration.
  Caller declarations do not establish runtime qualification. Actual file pins
  are checked before each child; the copied executable is checked again at the
  actual Popen site. Source/helper/capsule drift fails closed.
* Actual console SHA256 is
  `8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a`;
  actual template emu.cfg SHA256 is
  `e92b5817e28d4e96f4e7d038d64b365e356264d025e55b03f8184a0dd1817840`.
  Actual current-head fp_run SHA256 is
  `646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747`.
  Template reader/UI-capture helper and capsule contents are also inventoried.
* Guard forces console and a 16-process harness ceiling; it rejects a foreign
  executable/cwd/arguments or a second guest. It preserves launch emu.cfg before
  spawning and records its SHA. Allowed GD overrides and FP_NOLIMIT must exactly
  match the per-capture reviewed environment; ambient overrides are cleared.
* The watchdog requests termination at 55 seconds on the **exact Popen handle**;
  no process-name kill occurs. Scheduler/termination latency is not hidden:
  observed elapsed greater than 55, any deadline event, absent guest, leftover
  child, failed floor monitor or harness error makes the receipt FAIL. The
  watchdog observes C's 20 GiB absolute floor; entry and pre-harness staging
  require 24 GiB. A PASS never means physical-console or gameplay acceptance.
* `audit` requires a complete receipt for every expected capture, matching
  source/argv/input pins/console/config and actual elapsed <=55. Missing, duplicate
  JSON keys, partial or failing receipts refuse. An old shell printing PASS or
  ignoring its child's error cannot make this audit pass. It reports only
  `PLANNED_PROCESS_BOUNDS_COMPLETE`, with `runtime_qualified=false`.

The shared guest/trace locks protect cooperating lanes. Existing unadapted
cron/foreign launchers are not retrospectively controlled by these locks.
The installed RR lock excludes the known old RR cycle during the new entry.
Root must still use the standing fresh machine/process admission, give release
work priority, and stop other uncoordinated guests before authorizing execution.
A root coordinator crash is not a cross-platform process-supervision guarantee;
recheck live children before restarting cron or another entry.

## Source-only preparation / controls

From this directory in WSL:

```
python3 -B -m unittest -v test_adapter
python3 -B capsule.py prepare /root/probe/rr-safe-cycle23 /NEW/EXCLUSIVE/CAPSULE
```

The second command copies only source/reference files and hashes the named
console/template files; it creates no game image. A previously existing output
is refused. Do not point it at installed RR or a frozen evidence directory.
The 20 host methods use ordinary `/bin/sleep` children and an explicitly fake
nested-call recorder. Those are routing/deadline controls, not synthetic runtime
acceptance. Nested KOS/GD bodies make exactly three recorded wrapper calls;
mutants using the original reader and 60-second duration are detected.

## First actual observation, root only after review/admission

Prepare a new capture beside retained evidence, not inside the legacy capture.
Use the actual retained current-head **final GDI** and exact current main/all14,
assets and syms proof. Do not create g/c/QA bases just to boot the release image.
Use the original boot condition: `--seconds 45 --stop 'state title=' --grace 5`,
no warp/pad/base fixture. An existing byte-identical console capture can be
reused only after actual executable/programme/assets/fixture/symbol identity
closure; label it reused evidence, not a fresh run.

Root creates a configuration with status `ROOT_REVIEWED_CURRENT_HEAD_INPUTS`,
source/profile above, exact `expected_runs` (one cap -> full argv), `expected_env`
(cap -> allowed overrides, explicitly FP_NOLIMIT=0), and all actual Windows `input_pins`. These must
include console, template cfg, original harness, Windows Python, retained
programme/disc/assets/symbols and the actual root closure receipt. Bind
`closure_receipt` and `programme_assets_closure_receipt_sha256` to that receipt;
this is root's explicit review assertion, never generated acceptance.
`harness` is the capsule `_fp_run_original.py`, `harness_sha256` as above.
`console`, `console_sha256`, `template_cfg`, `base_cfg_sha256` are explicit.
`capsule_manifest_sha256` pins the actual prepared CAPSULE.json.

Provide Windows `config_windows`, `guard_windows`, `wrapper_windows`,
`windows_python`, plus the corresponding Linux `windows_python_wsl` and actual
binary pin (same hash under both spellings). Use exact `//wsl.localhost/Ubuntu-24.04/...` aliases for the capsule helper and config paths (backslashes also accepted).
`lease_path` must be a new exclusive
Linux path. `capture_paths_wsl` maps the Windows cap name for later `audit`.
`admission.phase` must equal `FINAL_GDI_BOOT_ONLY`,
`admission.release_priority_granted` must be true, and
`admission.maximum_new_c_bytes` must cover the worst new allocation. Reserve at
least 1 GiB for this one-capture phase (768 MiB reader cap + console/data/track01,
small receipts and margin); tracks02/03 are hardlinks, not new images. This is an
upper allowance, not a measured footprint. C must pass max(24 GiB,20 GiB+reserve)
with a fresh check at entry. Any later media/build phase needs its own fresh
24 GiB check and actual named-root admission.

`admission.command` is exactly `[windows_python_wsl, wrapper_windows, *argv]`.
The entry rejects any different command, including installed rr-cycle or a
bypass to the original reader. Root runs the **prepared capsule copy**:

```
python3 -B /NEW/EXCLUSIVE/CAPSULE/capsule.py hold ROOT-REVIEWED.json -- <exact command vector>
python3 -B /NEW/EXCLUSIVE/CAPSULE/capsule.py audit ROOT-REVIEWED.json
python3 -B /NEW/EXCLUSIVE/CAPSULE/capsule.py judge-boot ROOT-REVIEWED.json
```

The boot judge is separate from process bounds: it requires the title marker,
goal stop, original45s request/5s grace, no source errors/early exit and no bad
read/HALT/FAULT/MISSING rows. Its PASS is title-goal evidence only; both the bound
audit (including no deadline and explicit saved FPS yes) and this semantic judge
must pass. Neither establishes New Game, full route, QA or hardware acceptance.

No shell-concatenated command is accepted. The Windows/WSL bridge remains subject
to root's first actual console validation; host controls do not certify that OS
integration or a game gate. If it fails, preserve the new capture and report it.

## Minimal explicit patches still required for a whole quick+QA cycle

These are concrete activation blockers, not implemented safety promises:

1. Replace private rr-cycle `trees()` with clean exact-SHA admission of TWO NEW
   owned source trees; no checkout-f, worktree prune or shared submodule update.
   Give each tree one nonblocking lease. Every actual ch2/fp_twin/QA build must
   enter `/root/probe/d367-buildslot.sh` with inherited D367_SLOT_HELD cleared at
   the outer boundary (two SDK slots, jobs4). Release work has priority. Do not
   reuse shared rr/rr-b trees while cron runs. No SDK work exists in this unit.
2. Reuse actual byte-identical current release/twin/QA programmes/assets where
   proofs close, rather than blindly extract/master three new bases. Bind source,
   main/all14, knobs, template, syms and each old/new image's exact hashes. Reuse
   does not become a fresh measurement. If any missing arm needs building or
   mastering, estimate its retained + transient named-root union **first**; keep
   24 GiB at every stage and 20 GiB absolute, with root's actual admission. The
   old script itself describes ~2 GB peak per sequential fp_master base; a full
   cycle also overlaps candidate, extracted tree, g/c bases and QA raw/zip/base.
   Do not treat current C free or a 1 GiB boot allowance as full-cycle admission.
3. Use the private rr-jobs/rr-flycast and private fullplay copies for BOTH quick
   and QA. Bind the generated job list/scripts and ALL expected nested caps
   before running. Quick has boot+h2+required-census+two KOS+GD; QA has boot+warp+GD.
   Keep the original source-derived census scope; unknown diff means all rooms,
   not a smaller silently accepted subset. Aggregate retained capture allowance
   must be admitted, not N times an uncharged per-capture limit. Start with the
   boot phase above, then review whether the complete 53-second profile is useful.
4. Preserve rr-judge's semantic predicates verbatim, changing only its global
   REPORT writer to a NEW private report and binding a private read-only prior
   metadata snapshot. Require the independent complete bound audit in addition
   to semantic PASS. KOS's shell can print FAIL and exit zero; child rc alone is
   insufficient. Require both quick and QA to pass, no `||true` promotion.
5. Remove private cycle/QA cleanup of old candidates, work, source, evidence,
   cache entries and global metadata. Do not run installed cleanup helpers.
   Before any later deletion of this cycle's own rebuildable intermediates,
   inventory exact root/member/type/inode/hash in an owned manifest and receive
   root's bounded deletion admission. This adapter performs **no legacy cleanup**. The pinned reader
   normally removes its own new capture track links at exit; the guard writes
   their device/inode/size manifest before launch and permits only those exact
   same members to be unlinked. Changed/foreign files are retained and refuse.
   It never removes the linked source media or prior capture files.
6. Keep the installed canonical rr.lock through the whole new cycle, no bypass
   via RR_LOCKED. Do not install another watcher/cron. Old cron terminal status
   plus actual live-process check must precede activation. The new entry cannot
   qualify the already running old 60/300-second harness profile.

Source/runtime recipes and the production DATA line are unchanged. There was
no actual SDK, Flycast, image allocation, cleanup or new resource census while
preparing this unit. Root owns source review, activation, actual bound receipts
and game acceptance.
