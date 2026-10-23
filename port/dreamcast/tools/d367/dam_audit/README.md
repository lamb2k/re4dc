# Dam missing-actor audit controls

Read [the findings and boundaries](../../../docs/D367_DAM_MISSING_ACTOR_AUDIT_20261023.md).
The runtime knob is `R10C_SPAWN_LIVE_GUARD=1` (default 0); it requires the
existing `EM_READ_RETRY=1`. Keep the baseline `ea969bb2` available in Git.

Run from the repository root with fresh output directories:

```bash
python3 port/dreamcast/tools/d367/dam_audit/check_missing_actor.py \
  --output /tmp/re4dc-dam-audit-host

python3 port/dreamcast/tools/d367/dam_audit/build_controls.py \
  --output /tmp/re4dc-dam-audit-target \
  --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/pinned-kos-source \
  --sdk-root /path/to/sh4zam-sdk
```

The host runner extracts production functions and narrowly delimited failure
frontiers; it instruments their external service calls and supplies actor
creation outcomes. It does not perform real model construction, disc I/O,
task scheduling or rendering. Successful/existing-failure action sequences
are compared across baseline/absent/zero/on; retired actors are checked at
all three spawn attempts. UBSan covers these controlled host executions.

The target runner derives complete current room compiler commands from the
public Test22 recipe, separately for the baseline Make tree and candidate.
It obtains `MODULE_ARGS` from Make and runs the repository's source-only
module manifest generator into the output directory. It compiles the full
room TU, compares disabled preprocessing and objects, measures sections and
static stack, checks knob wiring, and saves an independently compiled
current `cEm` dispatch probe. PVR declarations are patched in a temporary
header overlay by the established public-profile helper; installed KOS and
SDK files are unchanged. Generated outputs stay outside Git.

The target gate does not build or relink an executable/overlay, run KOS
library patch checks, or reconstruct the original public Test21 program.
The original crash address mapping is cited from the existing release
identity audit. No game or BIOS assets are needed or distributed.
