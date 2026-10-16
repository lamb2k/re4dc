# Independent review: three exact r101 part coalesces

Date: 2026-10-16. Reviewer: vertex_data_locality, independent of candidate author far_shell.

**PASS for bounded model and visual pricing with the reviewed cxt16baserW executable and all six candidate assets.** This is host asset validation plus source review. It is not measured performance, runtime visual acceptance, or physical-console acceptance.

## Inputs and scope

- Source assets: /root/probe/codex-ch1-render-20261015/assets/spatial32v3
- Candidate assets: /root/probe/codex-batch-coalesce-t15-20261016/candidate/assets
- Runtime source examined: /root/probe/codex-cpu-t15-20261016/tree
- Runtime settings examined: /root/probe/codex-cpu-t15-20261016/builds/out-cxt16baserW/resolved-knobs.txt
- Executable identified by parent: cxt16baserW, SHA256 1f98fe56859c114ad09a818dd4b6f33658c42c73d11229186ec5ad9428cef8c6. The reviewer did not independently execute or rehash the executable.
- Pairs: mesh 206 parts 175/176; mesh 208 parts 195/196; mesh 209 parts 219/220.
- Runtime constraints confirmed from settings: MESH_LOD=1, MESH_PRIME_LAZY=1, PS2_INTERIOR_CULL=1, PS2_PVS=0, PS2_WORLD_HDR_CACHE=1, PS2_WORLD_LEAN=23, PS2_WORLD_R11F_OWNER=0, PS2_WORLD_SOURCE_OWNER=0, PS2_WORLD_SOURCE_TEX_PREP=0, PS2_WORLD_TRANSITION_OWNER=0, TA_GUARD=0.

## Independent host evidence

verify.py saves the independent Python validator used for the review. It imports the established ps2_world_far_lod parser, not the candidate converter. It separately validates ranges, strip references, merged part pools, cluster/level memberships, byte changes, and traversal order. host-invariants.json is the saved result from that review, with the status label narrowed to host invariants to separate it from the manual source review.

Both R4IM files pass parser CRC and structure checks. Each file differs by exactly 16 bytes, all inside the twelve intended count words and header CRC. File lengths, header counts/offsets, all mesh records, meshlets, vertices, colors, strip bytes, palette, clusters, and levels remain identical. Sidecar and ID files are byte-identical.

There are 554 identical ordered pass -> placement -> cluster instances, including effective sidecar state, remaining MeshPart flags, and exact UV float bits. This is a symbolic traversal equality across all stored clusters, not a claim that all 554 are drawn in a frame. All 103 meshes used by protected placements retain their part and part-LOD records. Protected rows include sky rows, IDs below 250, and gate placement IDs 209 through 222; gate-to-mesh mapping is unchanged because all placements and mesh records are unchanged.

The two inputs and outputs each retain 16,757 strips and 67,659 stored strip corners. Nonempty parts change from 238 to 235; total table rows and mesh part ranges are unchanged. Merged all-level corner counts for the three pairs are 112, 160, and 32 (28, 40, and 8 strips). These are asset census counts, not post-clipping runtime counts.

The active L5 strip-group file admits against the candidate L5 mesh and shared sidecar; its group record payload is identical. The padded L0 strip-group file retains the source fixture's intentional length/mesh-identity admission failure, so L0 fallback stays ungrouped. The reviewer does not describe that padded file as valid L0 strip-group data.

All six file capacities and allocation inputs remain unchanged.

## Source review and why the range merge is bounded

References below are relative to the runtime source directory above, at the source read during this review.

- port/dreamcast/room/instanced_mesh.hpp:180-236 and 297-309: MeshPackage admission permits zero-length part and part-LOD ranges. An empty part_pool returns false. Expanded A pools are contiguous and disjoint from later nonempty pools; B's preserved first index is harmless when count is zero.
- port/dreamcast/game/platform/native_static.cpp:4757-4810: the PS2 path binds by sidecar CRC/FNV/dimensions/pass/cull, not MeshPart.texture. Both pair rows have identical effective sidecar state and exact UV grid bits. The source-only texture index difference is 1 versus 2.
- native_static.cpp:2478-2544: selection reads unchanged global cluster/level/meshlet entries, bounds and errors. Placement matrices, lod_scale, culling state and source order are unchanged. The active PS2_PVS=0 matters: an external part-relative PVS layout would need a separate audit.
- native_static.cpp:2547-2581 and 4766/4821: an empty B row still performs setup, run/result bookkeeping and increments existing parts/native counters, but draws zero clusters. It never reaches bind or borrow. This candidate does not remove full part-loop cost or lower those counters.
- native_static.cpp:2080-2258: gather and transform data are refreshed per meshlet; cache constants depend on identical UV grid, UV offsets, alpha/LUT and near/far state. Reused strip-group plane coefficients depend on the unchanged placement matrix and near plane. skip_clusters defaults to zero on this PS2 path.
- native_static.cpp:873-919 and 4794-4810: the six-word key is stack-local but used synchronously through run and end_direct; no pointer escapes. The merged A direct window uses the same effective key and projection as B would use.
- port/dreamcast/game/platform/native_ui.cpp:7704-7829: cached headers check key, dimensions, pass/cull/fog, valid entry and VRAM pointer. The same placement keeps fog, sky treatment and modifier-receiver state. The texture is marked with the current frame when its header reaches TA, pinning it for the scene. PS2 world UV scales remain one.
- native_ui.cpp:6196-6207: direct_end unlocks store queues, accounts slots and resets model_used. It does not change UV state or unpin the texture.
- The active owner/source-preparation knobs are zero, so part-local transition/R11F UV callbacks and texture-acquired callbacks do not introduce different behavior across these three boundaries.

The plausible saving is zero to three redundant binds/direct-end/cache setups when both members of a pair draw. Culling can make that number smaller. No fixed per-part fee or measured saving is claimed.

## Limits and next gate

Source inspection and host checks support launching the bounded comparison. Resource-failure behavior, header/touch counters and direct-window length can differ. Runtime captures and model measurements remain the parent's next gate; hardware acceptance remains separate. The reviewer performed no source or asset edits, build, emulator launch or performance-model run. Saving this review and its verifier only adds evidence under the review directory.

To replay the host check:

    python3 /root/probe/codex-batch-coalesce-t15-20261016/review/verify.py

Compare its JSON to host-invariants.json and its candidate hashes to candidate/invariants.json. The script uses fixed paths intentionally and writes only stdout. The manual source conclusions are not automatically revalidated by the Python script.
