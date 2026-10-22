# Bounded world scratch experiment

`WORLD_SCRATCH=0` is the default. It adds no object, runtime hook, ordinary storage or cache-mode transition. No production recipe changes. CPU_BACKFACE must be0 in every arm.

A single enabled image compares:

| Arm | Operand cache | Projected records | Outcodes / packet reservation |
|---|---|---|---|
| A (0) | Normal16KiB | Existing RAM tail,8192B | Original256B /8448B total |
| B (1) | Reduced8KiB, OCRAM enabled | Same RAM tail | Identical |
| C (2) | Same reduced cache | KOS `.ocram`,8192B | Same RAM tail and reservation |

The only renderer pointer replacement is the projected array after `MeshDraw::borrow` has subtracted the original264 packet slots. Outcodes are computed from the original RAM tail before replacement. Source/gather/LUT, meshlet/strip selection, arithmetic, clipper room and SQ emission remain unchanged. Flags/oargb use the existing full or lazy per-entry prime before consumption. Every mode or storage-pointer epoch resets retained lean prime pointer/count. No MOVCA/discard or baseball address/index-mode routine is imported.

The full8192B `__ocram` array consumes KOS's complete linker range, forcing conflicting linked allocations to exceed its bound. Its contents are never statically assumed valid; no OCRAM read occurs before admission, mode activation and the ordinary entry prime/transform. No ordinary8192B BSS buffer is added.

## Admission and runtime control

Enable only an isolated benchmark image with `WORLD_SCRATCH=1`, `CPU_BACKFACE=0`, `NATIVE_STATIC=NATIVE_MESH=D349_RENDERER_STACK=PS2_WORLD_DRAW=PS2_WORLD_MESH=MESH_DIRECT=PVR_STREAM=1` and the source's normal mesh fastpath. Existing Make dependencies still apply. `MESH_FASTPATH` defaults1 in the validation fragment; overriding the actual source fastpath off fails compilation.

Admission is initially closed. Main must review the **exact final ELF**, all runtime modules and the resolved KOS root before calling `re4dc_world_scratch_admit(1)` on the source frame-owner thread. The argument is a reviewed protocol version, not evidence or a cryptographic proof. Never call it just because host/object tests passed.

Run `audit_image.py --elf FINAL.elf --kos RESOLVED_KOS --module EACH_RUNTIME_MODULE.elf --complete-module-roster-reviewed --output PRIVATE_RECEIPT.json`. Supply every runtime module (repeat `--module`), then manually check their source/disassembly for inline CCR writes, hidden OCRAM access or retained projected pointers. This script checks final EXEC type, sole8192B symbol at KOS0x7c001000, alignment, NOBITS/NOLOAD, pinned KOS source hashes and module section/symbol conflicts. It deliberately rejects relocatable objects. Its receipt never replaces the manual complete-module review or runtime CCR check.

Both inspected KOS roots (`/root/work/kos-re4dc-d336`, `kos-re4dc-d367`) have identical cache.s/cache.h/shlelf.xc bytes; hashes are pinned in the audit tool. Existing KOS `dcache_toggle_ocram` calls `cache_write_ccr`: short IRQ mask, P2 jump,512 tag entries, CCR update, eight NOPs, restore IRQ. OIX/IIX remain0. No KOS or linker source is changed. Unsupported CCR (including existing ORA/OIX/IIX), wrong owner/IRQ context or unexpected linked array mapping rejects admission.

After admission, request an arm with `re4dc_world_scratch_request(arm,iterations,room)`, where iterations is1..600 and room is the currently reviewed PS2 room. This records a pending request only. The next real drawn/skip frame boundary latches it. Warmup/sample scheduling belongs to the harness; use an identically sized window in each arm, warm up after entry and collect the same interior frames. Starting another arm restores the old lease at a quiescent boundary. Stale-room requests are dropped. A room/movie/abort cancellation drops pending requests as well.

Read `re4dc_world_scratch_stats()` on the owner thread: requested/actual arm, remaining iterations, completed iterations, borrows, entry/exit counts and microseconds, prime/storage epoch and fault counters. actual3 means unknown external/failed CCR state, never a valid A comparison. No faulted sample is performance evidence. No timer is added per vertex or meshlet.

## Lifetime

The **mode lease spans a bounded multi-frame window**, including skipped iterations and other whole-frame CPU work. It is not switched at each meshlet or each frame. Each iteration separately opens admission to synchronous projected-pointer borrowers. Only one borrower may exist; nesting/reentrancy and foreign-thread borrowing fail closed and abort the model packet. MeshDraw destruction retires the borrower. End-frame guards carry unique frame tokens, so an old/reentrant guard cannot end or cancel a later frame.

At window end, explicit cancel, missing/failed frame, room retirement, packet abort, movie open/upload/close or source-movie handoff, admission closes immediately. Restore waits until all synchronous borrowers retire. An in-frame cancellation revokes that frame token; a late end is harmless. Failed readiness and late stream aborts are covered by the UI end guard. Wrong-thread requests/releases cannot borrow or unpin memory; restoration waits for the owner thread to return to a boundary. Unexpected CCR changes revoke admission and are never overwritten; restore does not guess at someone else's mode.

No async queue retains a projected pointer. The two direct-begin paths return the existing packet scratch to the synchronous MeshDraw; strip paths copy all selected words to SQ/TA before returning. Pipeline1's presenter receives the present bool/faults; pipeline2 receives a KOS present decision. GPU and delayed presenters consume their own copied TA storage. Pending GPU work is not a projected-pointer lifetime and does not confer OCRAM ownership. `sq_lock` is never used as proof of exclusive OCRAM ownership. Inline modules/IRQ ownership still require final-image audit.

## Measurement and acceptance

A versus B measures the reduced-cache effect on the complete frame, including actors, source simulation, UI, audio threads/IRQs and the renderer. B versus C isolates projected-record placement. Report inclusive world time and total CPU/frame time separately; do not add overlapping rows. Mode-entry/exit time is reported separately in Stats. Existing `completed_frame.render_wall_us` takes its endpoint before the end guard and therefore does **not** include an exit toggle; an external whole-frame benchmark must include that cost explicitly. Any later production per-frame transition variant must charge both transitions and cache refill cost to every frame. No source, host, object or instruction-model result establishes a gain.

Use identical build, room/view, camera, geometry/assets, CPU_BACKFACE0 and proven arena/texture-residency settings across A/B/C. Record shell state and View setting, no VRAM refusal/reload and the actual asset package. This work neither edits nor fixes the arena; a changed cache layout can mask its physical-only fault. Final gates remain whole-program default-off identity, final ELF/module ownership, KOS48KiB, r100s30 heap4, exact emitted words/outcodes/TA, console-mode Flycast correctness and the matched physical-console world/total-frame comparison. No target link, guest, disc or hardware run was authorized to this source lane.

## Checks

Run `python3 port/dreamcast/tools/d367/world_scratch23/run_tests.py` for the real engine, portable transform/prime/indexed emit, packet canaries and negative controls. It verifies bounded draw/skip windows, pending/live arm requests, admission/layout, nested/foreign owner, stale room/frame token, failed toggles, foreign CCR changes, cancel/late abort and delayed copied TA bytes. Default/explicit0 runtime objects are both empty and identical. Audit parser and Make admission rejection controls are included.

Target-object receipts are private in the lane handback. They compile only the three touched units under actual Make flags (sparse module-generation suppressed for object-only work), with movie-enabled pipelines0/1/2 on d367 plus d336 integration. Changed-off renderer objects compare byte-for-byte with untouched base64a28a7b after stripping debug information (DWARF line tables naturally differ). This does not establish final linked-program identity or runtime hardware correctness.
