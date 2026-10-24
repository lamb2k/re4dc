Corrected427 KOS48 retest — preparation only
==========================================

No staging, SDK, media mutation, guest or memory test has run under this kit.
H2 remains held. Original ON4000/4016 failures, original QA/census media,
all captures, and v1 capacity-HOLD/full inode inventory remain untouched.

Root explicitly superseded the proposed all-history4GiB limit with a NEW
reviewable allocation: historical baseline + new delta<=1.25GiB and
aggregate<=6.5GiB; C admission26GiB and floor24GiB. This changes no earlier
sealed allocation. BASELINE.json hashes every preserved media/work/kit
member and records actual path, bytes, dev/inode/nlink. Baseline is
5,278,682,286 unique bytes. Immutable source programme exports and installed
host dependencies are read-only inputs, not new staged copies. Every new
kit/work/final/capture inode is charged to delta and aggregate; only actual
same-dev/same-inode hardlinks avoid doublecount. No deletion or cleanup.

One new final ON track set only, at:
C:/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on
New work root: /root/probe/gc-motion24-kos-budget-retest-media-v2.
OFF is the exact existing qa-memory-media-aab-v1/base-off, reused read-only.
The complete OFF disc1715-file/IP/all14/6redirect readback passed in host
controls against the corrected e016 programme binding. No new OFF ISO.

Corrected target source427784b1f48aa30742850bb5025925ab619b740e, durable
47-file export MANIFEST73bc1537, terminal4cccda25, independent target review
3d207941/readback130bb13f are exact inputs in BINDING.json. OFF raw e0168b78;
ON raw9e3758b23940ab1ce88fcd37eae3dff28efb19086bd044f8552ff81350e33876.
The original1697-member candidate manifest/IP are authenticated. Only15
programme members and3 blank redirect fixtures differ in the staged tree.
Unchanged asset members are hardlinked to the existing authenticated source
inodes. There is no alternate boot/injection or complete new asset copy.

Executable staging uses authenticated direct-source adapters around the
reviewed census-stage812c92f2 protocol: same fresh paths, monitored children,
genisoimage/official redirects, all-file and IP readback, owned-stage lock,
signal/group cleanup, and no guest. Adapters explicitly rebind source,
binding, resource monitors, official ISO direct-source loading, isolated
Windows admission Python, legacy validation-only fixture pathname to the
authentic original48KiB fixture, and diagnostic label to noncensus QA.
Original template files remain byte-identical. Before any writes, the
complete baseline bytes/inodes and link counts must match; afterward only
increased link counts are allowed, with all original bytes/inodes intact.

Root launch only AFTER independent review and a separate exact stage grant:

  export GC_BUDGET_RETEST_TOOLS=<SHA256 TOOLCHAIN-SEAL.json>
  export GC_CENSUS_STAGE_GRANT_SHA256=<SHA256 new ROOT-STAGE-GRANT.json>
  /usr/bin/python3 -I -S -B '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-retest-media-prep-v2/launch.py'

ROOT-STAGE-GRANT-TEMPLATE.json is deliberately approved=false and contains
placeholders. Root must separately pin baseline/binding/seal and both new
caps; the old grant cannot authorize this stage. Root is responsible for
an explicit valid grant. No invocation without review/authorization.

readback.py is executable read-only with --tools-sha256 <seal> --arm off/on
--out <fresh absolute metadata path>. Future stage must yield complete ON
and PAIR-STAGE-COMPLETE.json, then independently cleared poststage readback.
No retry or overwrite; any partial output is preserved on failure.

GUEST-PROPOSAL.json is plan-only: four serial OFF/ON frag0 then frag1,
original normal fixture held49152,45s route,55s exact owned console child,
hardcoded stat3 slot then global trace16. Current ELF log/head/stage values
come from exact durable nm. FP_NOLIMIT=1 and actual aica.LimitFPS=no must
be checked before Popen. Use independently cleared Pillow3bcff1c5 with
actual Python-I-S-B and fresh absolute absent-X checked BEFORE Python
starts. The proposal does not supply or authorize a guest controller;
root must implement new post-slot admission/grant/cap checks, verify
config and require stage/readback acceptance before using those argv.

Each case must witness actual held49152, correct fragment, original route
goal, min headroom>=4096, noOOM/HALT/MISSING and no deadline fire. Images
alone prove none of those. No memory/performance/hardware or H2 acceptance
follows from source/host preparation or static target success.
