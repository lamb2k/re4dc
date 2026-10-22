# WORLD36 evidence decoder for canonical 69f

This source-only tool prepares keyed observations for the canonical mipmap programme. It does not attach to Flycast, read a process, write memory, build a programme, or modify runtime code. Benchmark owns the observer and scene/phase latch. This unit observed no guest frames.

The fixed identity is source `0425534d848973c1dae3ab960d0006ac9afcf363`, programme `733afabf6567a9f086eacb48b70559aef764cf52a5b534f44602da3a8bc68a9e`, ELF `69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae`, and canonical1004 pack `89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62`. Other ELF identities require a fresh reviewed binding.

## Files and use

`bind_69f.py OUTPUT.json` hashes that ELF and streams fresh DWARF through the benchmark owner's existing parsers. It selects the unique native_ui CU, follows type/specification references, records 6 concrete type layouts and member widths, and binds 13 unique absolute globals including the actual 448x224-byte Entry array. It reads only the previously sealed canonical WORLD36 packages and original part-binding records. It verifies their package SHA and descriptor-plus-payload CRC; it emits complete native headers/descriptors, their expected hashes, source/scoped keys and 164 material-part bindings. Existing output paths are refused. Peer parser/source SHA identities are recorded. The retained selected binding is `bindings-v3.json`; earlier v1/v2 bindings are preserved as development artifacts.

`decode(snapshot, binding)` in `snapshot_oracle.py` consumes raw byte snapshots supplied by a separately qualified observer. The observer must authenticate the process/ELF identity, perform bounded RAM reads, bracket all reads with the supplied scene and direct tuples, and acquire two identical Entry/header/descriptor/table/header samples. The pure decoder cannot authenticate caller-supplied bytes or establish that no mutation occurred and reverted between samples. It performs no retry or process discovery. Missing keys are not evidence of nonuse.

The snapshot is a dictionary matching the executable fixtures in `test_oracle.py`: ELF SHA; Entry address and before/after hex; header/descriptor/PVR table addresses and before/after hex; owned-texture byte/address; stable `scene_before/after` with room_id/source_frame/ui_frame. The optional direct channel adds stable `guard_before/after` containing frame/direct_open/model_handle/model_used/model_pending/model_packets/frame_ready/stream_scene/stream_aborted, and the exact computed CPU packet header address plus two 32-byte hex samples. Scene/phase qualification belongs to the benchmark observer. Extra scene identifiers can be carried through the scene dictionary.

## Evidence levels

- `RESIDENT_DESCRIPTOR_FORMAT`: exact canonical Entry key, Package pointer chain, native header/descriptor, upload/ownership state, VRAM pointer table and compatible source-room binding. The asset SHA and descriptor/payload SHA are expected offline identities; resident metadata does not establish the observed VRAM payload contents or recompute payload CRC. The observed CRC is the live header's field. Preload alone can satisfy this level.
- `COHERENT_CPU_DIRECT_PACKET_HEADER`: adds a coherent direct-open tuple, matching Entry/frame, bounded packet address, repeated CPU staging header, textured polygon/list, physical TSP dimensions, repeat policy and exact TCW format/address join to the sampled VRAM pointer. TCW bit31 is decoded as mipmap enable, bit30 as VQ, format as RGB565. Filter and mip bias are reported as command fields. This is a CPU staging observation, not an accepted TA primitive or proof of submitted geometry.

Both levels always return `actual_submitted_header=false`, `actual_submitted_vertices=false`, `draw_proof=false`, and `chosen_LOD=UNAVAILABLE`. No Flycast outcome, release gate, hardware timing/FPS or physical Dreamcast acceptance is supplied. A completed-state phase record with direct_open=0 cannot supply the optional live-open header channel; linking them requires separately authenticated sequencing.

## Exact remaining hook

The existing world direct begin copies a header to SQ and flushes before setting direct_open, but the global latch/model_handle is shared with generic/model/Leon switching paths. The observed model_packets buffer is a CPU staging copy; it is not SQ MMIO or a TA-accepted command log. Model direct end clears the latch and increments aggregate direct_parts/direct_slots without a stable per-key window record. A matching stable staging header therefore does not establish its exact submitting caller/part, submitted vertices, raster, presentation, or chosen mip level.

A future reviewed, default-off hook could publish an immutable per-world-window event with a sequence bracket: scoped and source key, Entry generation, source/UI frame, room, exact call-site/window cookie, TCW/TSP/address, abort epoch, and actual positive vertex count after that window's SQ completion/unlock. Zero vertices must remain header-only. An observer could double-read that event and link it to a separately qualified phase. Even that event would establish submission only, not TA acceptance, visible raster, presentation or a selected hardware LOD. Chosen LOD requires separately scoped renderer/hardware sampling evidence. This unit implements no hook or runtime instrumentation.

## Verification

Run `PYTHONDONTWRITEBYTECODE=1 python3 test_oracle.py bindings-v3.json tests-v3.json` after selecting the sealed binding. All 36 real expected asset records are used in synthetic RAM snapshots. There are 108 positive cases and 720 meaningful rejection cases covering identity/stride, ownership/pointer chains, malformed metadata RAM, canonical metadata mismatch, scene tearing/room mismatch, direct-frame/tuple tearing, packet pointer/header tearing, mip/VQ/address bits, dimensions, clamp and polygon class. Every positive keeps draw false and LOD unavailable. These are source/host decoder tests; guest observations=0.

Consumers' independent actual69f binary evidence is pinned by the sealed receipt: linked KOS routines preserve the full format through TCW word3 store at +12. It supports the bit decoding but does not upgrade either observation level to draw evidence.
