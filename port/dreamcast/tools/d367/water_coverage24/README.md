# Early PS2 water: authenticated source and default-off candidate

The scope covers all three early landmarks: opening bridge/ravine/pond r100, lake-house/fish basin r107 and boulder/shallow stream r10a. Later dam/rain work remains separate. This lane implements a bounded r100 material candidate and all-three source/diagnostic coverage. Appearance, current programme, memory, progression and console acceptance remain open.

## Actual original paths

Actual PS2 st1_0.rel (92760 bytes, SHA256 01718aa3fdb13d69bc00d4b577a09231d33cf612eee79a1c489c86813c496f5f) R100Init calls setup0x6500. It applies wildcard texture247, blend255, alpha240, shader2, refraction30/128 and64x64 target to object IDs0/1. Actual SLUS_211.34 (SHA256 465d144f526603d0dcc35ad1fdb4e82cc3a1481c22289f321482cc910fb9f1ad) SmdSetup registers by SMD byte51; SmdGetObjPtr indexes that same table. Unique IDs0/1 are placements0/1 BIN129/130. Original meshes contain94/147 triangles; no synthetic plane is used.

The actual PS2 TexBlend0x25ca40 path replaces the authored TEXHeader with the target manager TEX0. Five original callers use this path. Authored UV remains the coordinate source. The earlier full-frame captured-scene/refraction prerequisite was inferred from recovered GC RefractShaderSetup and is explicitly withdrawn. No new framebuffer capture or GC shader approximation is required by this authenticated PS2 path. bind_ps2_texblend.py pins the actual instructions and records the limits of the timing reconstruction.

The PS2 target is64x64 GS PSMCT32 (16384 bytes). The existing DC PVR RTT owner is64x64 ARGB4444 linear (8192 bytes), captures frameN effect packets and renders before frameN+1 main scene. Reduced color/alpha precision, one native frame delay and OP0->TR2 alpha treatment are explicit DC candidate differences; exact GS pass/blend semantics are unqualified.

r107 has two original PS2 water rows and r10a four. bind_early_tables.py reproduces their existing water_ps2_table.inc rows exactly from actual original EFF. These existing WATER_PS2 paths are not duplicated. RE4DC_EARLY_WATER_DIAG=1 reports seen/quality/inactive/missing/native-rejected/emitted row masks; it changes no activation, lifetime, textures or gameplay. Root must observe the actual failed path before a targeted repair. Source equality alone does not prove residency or visible pixels.

inspect_source.py binds original DAT member4 SMDs, embedded TPLs and418 BIN spans to existing inputs; room placement/BIN counts are283/148,71/69,228/201. These files are evidence, not an automatic positive asset-origin certificate.

## Current selected r100 geometry

bind_current.py independently decodes the selected-current1697 R4IM and compares level0 strips and UV to original PS2 BINs. Current part0 retains94/94 source triangles and winding; part1 has146/source147, replacing three original triangles with two. Maximum position-axis errors are0.752/0.598mm. Original normalized UV matches within0.000075/0.000064. Exact original geometry identity for part1 is explicitly refused. Existing selected geometry and its reviewed WORLD_RECT21 compatibility are retained; no payload or CRC is changed.

Pins: R4IM1537920 bytes/bodyCRCfb35ea9c; current mip22b R4PW CRC25d5daaf; original R4ID CRC14118acd and283 IDs. Both original selected materials are pass0,cull2,texture42,128x64,key8fe18585-328f7858. These exact pins restrict the candidate but do not grant provenance. Root must validate the real selected geometry proof and every accepted texture entry independently.

## Candidate implementation

RE4DC_WATER_R100_MATERIAL defaults0. No Make/recipe changes occur here. With it enabled, native_static.cpp routes only authenticated placements/meshes/parts0/1 to the existing TR2 phase; it preserves authored geometry, cull, fog, source visibility/object lifetime and transforms. The two draws use alpha240 and bypass mutable chunk/replay submission after flushing prior work. Missing/stale material authority refuses the surface. Other placements keep their original paths.

water24_material.hpp defines a bounded borrowed descriptor, no allocator or asset admission. Request binds current object pointer/serial, room generation and selected geometry proof. Target binds existing RTT owner/texture, actual PS2 source target/slot, geometry generation, room generation, allocation epoch, capture/render frames, dimensions, format, contributor receipt/serial and actual completed fence. Root must independently verify live origin, visibility and actual source-target ownership; copying descriptor fields cannot grant authority. UV scales remain1/1.

water24_rtt_state.hpp and pvr_rtt.inc reuse the sole existing RTT allocation and actual pvr_wait_render_done. No extra allocation or GPU wait is added by metadata. Existing target allocation still occurs lazily when an effect captures into a wanted target; enabling the feature can therefore activate the existing8192-byte target, RTT scene and existing wait. Runtime cost and peak VRAM are not measured. Metadata serials never reset at room changes and refuse wrap. Dimension changes invalidate tokens. Any unresolved/foreign contributor, packet overflow, changed context, failed scene/fence or stale frame prevents a positive target receipt.

The root-owned native_ui bridge supplies acquire/enter/leave/current/current_valid, capture_context(slot), capture_contributor, capture_fence_ok and room_generation. It must mark only the existing actual r100 target wanted, independently validate accepted PS2 contributors, and bind the live ARGB4444 target before ordinary image/cache lookup. Native_static supplies geometry/source_current; the RTT owner supplies rtt_target/rtt_current. No Re4dcModelPart ABI change, ice overlay, duplicate owner or framebuffer allocation is introduced. PVS qualification must independently establish that these two transparent surfaces do not become opaque occluders.

## Host verification and remaining gates

Run test_material.cpp and test_rtt_owner.cpp with a host C++11 compiler and the platform include directory. They test the actual descriptor/state header and actual modified PVR RTT include using bounded PVR stubs; they are host source controls, not hardware measurements. test_off.py compares default-OFF preprocessed tokens against base140a699f8 across four configurations, including scenery chunk/select/batch paths. test_diag.py separately exercises the actual diagnostic helper and its OFF identity. These checks do not establish SH-4 object/ELF/payload identity or target compilation. Root owns SDK/actual programme, all-three diagnostic runs, paired stills, texture ancestry/residency/memory, route and physical-console gates.

Private original bytes and reports remain outside Git under codex-lanes/water-coverage24 and re4-assets-private/water-coverage24-20261024. Source tools refuse existing output paths and cap scans at256MiB/120seconds. No asset conversion, pruning, stage, guest, publication or SD copy is performed here.
