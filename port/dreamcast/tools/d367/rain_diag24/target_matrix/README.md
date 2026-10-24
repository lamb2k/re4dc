Preparation only: selected SH4 rain diagnostic matrix
====================================================

Frozen source is da413ff058f88fa136375ecff629610fc59c0e51, with runtime blobs from fdb5ed4212fc78823f625ab75b78cc237cfd181a. Baseline is bca44d58a1fa0a51fd87ba94deba8cba925c8998. The source edit claim is released. This directory changes no runtime, recipe, assets or original evidence. No SDK command was used to prepare or test these helpers.

`PINS.json` binds both actual normal rP Make log command lines, their original non-system dependency and complete resolved-knob files, frozen source/header blobs, the normal provider ELF, wrappers/compiler/assembler/binutils byte hashes, environment scripts and these helper bytes. Primary exports are generated from those immutable Git objects only inside a fresh owned RAM root. Headers consumed by the prior normal build must be identical between the frozen commits. Newly discovered full dependencies must remain inside that export or the admitted KOS/ports/toolchain roots. A new repository header fails closed until preparation is explicitly amended.

The matrix has eight cases, two selected objects each: baseline feature0/1, then new diagnostic absent/0/1 crossed with feature0/1. Feature0 uses actual OFF normal argv; feature1 uses actual ON normal argv. Only filter06 receives the normal `RE4DC_RAIN_R10C_DC=1` macro; espgen44 receives neither feature macro in normal Make. For diagnostic absent and 0 the actual Make default is absent; explicit0 is an additional synthetic compiler control. ON adds exactly `-DRE4DC_RAIN_R10C_DIAG=1` to both selected units, matching reviewed Make wiring. The script retains the original flag order: filter06's effective optimization is O1, espgen44's later override is O2.

The explicit target-command differences from each pinned normal argv are the single owned output operand, `-fstack-usage`, and the selected diagnostic macro (none/0/1). Before compile, `-M` derives the complete dependency list and hashes each consumed file. `-E -H` retains actual preprocessed bytes and include trace. Compilation replaces MMD with MD and adds an exact MF/MT output to retain system dependencies; its complete dependency set and hashes must equal the precompile set. Dependency/output control flags are the only extra differences for those phases. The future wrapper uses a standard CPU PATH before KOS appends its pinned compiler/wrapper paths, and clears inherited include/compiler injection variables; these environment differences are explicit. `kos-c++` adds its pinned KOS_CFLAGS/KOS_CPPFLAGS via kos-cc; the run records those resolved strings rather than pretending the Make log already includes the wrapper expansion. No definition, source path, header path, debug information or section is normalized to manufacture equality.

Every case uses the same owned bench source spellings, working directory and temporary output spelling. Only the two owned primary copies switch between already authenticated bca/new bytes. The original trees and exports remain untouched. Sixteen raw objects, stack reports, full dependencies, preprocessed sources, include traces, strict strip-debug objects and eight partial relocatable pair links are retained. A partial link is not a runnable programme.

Host preparation checks (no SDK):

```
PYTHONDONTWRITEBYTECODE=1 python3 test_preparation.py
python3 matrix.py check --pins PINS.json
python3 matrix.py plan --pins PINS.json
bash -n run-matrix.sh
```

`matrix.py seal` is a one-time preparation operation: it reads pinned Git objects, prior command/dependency logs, existing ELF and tool bytes, and writes a fresh PINS.json. It never executes a compiler, SDK wrapper or environment script. Existing seal files cannot be overwritten. The preparation test uses small synthetic real ELF32/SH files in /dev/shm; these prove the checker boundary, not generated SH4 code.

Future root allocation is required before this command:

```
bash run-matrix.sh /absolute/preparation/PINS.json /absolute/ROOT-SELECTED-SH4-GRANT.json /dev/shm/rain-diag24-target-<fresh-owner-id>
```

The grant must contain kind ROOT_SELECTED_SH4_GRANT, authorized true, a unique grant_id, exact source/base/PINS hash/output/case_names and exact limits from PINS. The template has authorized false and is not an allocation. Public entry rejects inherited SDK slot state. It validates pins/grant before taking the canonical rain-diag24 tree lease and exactly one shared D367 SDK slot. Work is serial, jobs1. An exclusive RAM root is reserved only after allocation/slot and floor admission. The pinned SDK environment is then sourced in a separately bounded60-second child with owned bootstrap TMPDIR, shell trace and NUL-delimited environment receipt; its m4-single C compile probe and kos-cc -dumpversion are SDK commands and are deliberately included only after allocation. No source tree is edited by the selected compile harness.

Limits: 256 MiB process address space, 256 MiB total owned files (source/header bench, temporary outputs, logs and evidence included), 60 seconds per explicit compiler/binutils command, 360 seconds compile-matrix wall time, bootstrap60 seconds, outer wrapper380 seconds including setup. The outer deadline still bounds the combined run, so budgets do not add to420 seconds. Admission requires free RAM at least288 MiB and C free at least24 GiB. Root reviews actual available resources before granting. The bounded poll checks cap and deadline while a child runs; on violation or wrapper termination it kills only that owned child process group (a Linux parent-death signal also terminates the direct SDK driver if its exact Python owner dies), preserves failure, and refuses a completion claim. A failed environment bootstrap or outer timeout can leave a RESERVED root without matrix-result; readback refuses it. No automatic retry or output overwrite occurs. The next full-normal grant remains separate.

Independent readback (stdlib Python, no SDK process):

```
python3 readback.py --root /dev/shm/rain-diag24-target-<owner-id> --pins /absolute/preparation/PINS.json --out /absolute/new-readback.json
```

Readback authenticates every artifact and the old provider ELF. It requires all sixteen unit inventories, eight pair files, allocation/bootstrap files and every command/include log. OFF absent/0 must have identical allocated code/data/NOBITS metadata and allocated relocations, including resolved definition section/value/size/binding/type; both raw and stripped object hashes/equality are reported separately. Raw debug differences remain real differences. Strict allocated/relocation equality establishes only selected disabled generated code/data identity. Whole raw programme, all14 recipe definitions, normal startup image and loaded assets are later full-normal gates.

ON readback requires exactly one filter06 global128-byte NOBITS record, section alignment at least32 and symbol offset divisible by32. It reports actual selected text/data/BSS deltas, all `.su` self-frame rows and the pair's new external imports. Every new or changed external import, including weak imports, must resolve in the frozen normal provider ELF; new whole-cache imports are rejected. `.su` is compiler-reported self stack only, not call-chain stack or heap/headroom. ET_REL alignment/offset proves no absolute P1 address or final linker padding. Normal ELF linkage must later prove those facts.

Full per-object disassembly and relocations are retained. Structural OCBWB/OCBI/OCBP counts and an A0000000 literal observation are explicitly insufficient to prove cache semantics. Root must inspect the actual Filter06Init body, range-loop immediate128/start alignment/step32/termination (four lines), its cold-only control flow, record relocation/P1 location and every P2 accessor in selected target output. Verify no hot helper cache maintenance or hidden fallback, and inspect any newly referenced actual provider opcodes. No independent PVR packet acceptance, cache execution/coherence, physical duration, controller/archive ancestry, guest scene, appearance or pixel gate follows from this matrix.

PINS-PREP-V* files are preserved intermediate preparation seals only. They predate final helper changes, are intentionally invalid for current launch and never authorized or ran SDK work. Only PINS.json is the candidate final seal.
