# MipsFit and Dreamcast texture compatibility

Main reviewed the user's MipsFit reference while the mipmap and cache workers continued implementation. These are separate CPU and texture tasks.

## CPU placement: reuse the approach with SH-4 evidence

Reference: [Byterset/MipsFit](https://github.com/Byterset/MipsFit), pinned revision 33c02662ed0a2143bbfc37d572ddae5afd537c62, MIT license. The inspected checkout is /root/probe/mipsfit-reference-20261021. Preserve attribution if code is reused.

MipsFit builds temporal relationships between 32-byte code chunks, searches section placements that reduce cache conflicts, and replays the actual relinked program to check the result. That complements this port's existing C3 call-chain clustering in ordgen_c3.py. The port already has section-ordering scripts and a stale-order checker; extend that workflow and the existing timing model.

The upstream ELF reader requires machine 8/MIPS; its instruction decoder and trace importer are specific to MIPS/Ares. Cache replay and relationship graphs assume 512 lines and 4-byte instructions. The SH7750 configuration used by the port model has 256 direct-mapped 32-byte instruction lines and 2-byte instructions. Changing only the cache-size constant is insufficient.

Implementation sequence:

1. Extend existing hwtrace tooling with temporal chunk relationships, using verified ELF/overlay bytes and original execution ordering. Preserve actual SH-4 cache/index/uncached behavior and reject incomplete traces.
2. Compare candidate placement with accepted C3 order and unchanged baseline across village, farm and later scenes. Verify unique input-section ownership; fixed startup/vector/overlay sections remain fixed.
3. Rank with the existing timing model. Validate actual relinked ELF/map and final gameplay/resource gates, then measure matched console whole-frame timing before enabling a layout.

The read-only fit check confirms the retained Oct18 r101-fast-a program is EM_SH 42 and has 16 preserved instruction traces, frames 480..525 with stride 3. Program SHA: 8f97369c66337cd3bee6ed8f025cabfa89ed41138302d88898719ea4bc47181c. Its old model attributes 8.1153 ms/frame to instruction stalls. This includes the entire sampled frame and is not a predicted saving, current Test21 result or console measurement. No game code, linker layout or release changed. Local evidence: mipsfit-fit-check.py and mipsfit-fit-check.json.

The first diagnostic POC is now implemented and pushed as aa7c8cefd9609f7b715a819bc7b00842a51bd5eb on origin/codex/cache21-layout-poc, based on54cef5d1. Its7 tests pass, and replay of all16 retained traces matches the pinned158,164,423 instructions and1,414,147 fills exactly. The tool and validation receipt are in port/dreamcast/tools/hwmodel/cache21_layout. The source-bound private receipt is C:/Flycast-Evidence/re4-dreamcast/cache21-layout-20261021/r101-retained-final02.json. It labels conflict pairs, including MeshDraw/box_mask, but function labels do not prove movable linker-section ownership. No placement optimizer, new linker layout, relink or measured performance saving is complete. Existing C3 ordering remains the baseline.

## Textures: compatibility using native formats by family

Mipmap generation now has an implementation owner. Begin with an opt-in lower-level mip generator for existing square 16-bit VQ world textures; preserve original base indices/codebook and existing output when off. The first private candidate is the farm's 15 compatible keys, whose source-counted extra payload is 16,394 B. Actual allocation overhead and concurrent VRAM are separate gates. Continue through palette, rectangular/atlas, alpha and renderer-consumer contracts after this first path.

The farm checkpoint remains preserved. Source is now pushed through cfd60688327ef2b88ec06106d0097c156a897f23 on origin/codex/mipmap21. The combined29-world-package candidate converts696 of1488 world keys (508VQ +188 native twiddled16-bit), preserves5805 other pack members, independently decodes5376 levels and keeps every original base exact. Archive156254208 ->157874176B; added payload2335592B / rounded requests2343680B across the multi-room inventory are not concurrent resident VRAM or speed. Compact square PAL4 support is separately source-tested. Main owns the792 rectangular world keys' UV/wrap/edge and budget contracts.

The user's scope is the whole texture pipeline, including characters/bosses, effects and UI. The world batch is a starting cohort. The worker now classifies all6501 retained normal pack entries against actual consumers and implements confirmed compatible groups, while separate loose/low-quality and embedded paths remain explicit. Existing five Ganado mip keys are preserved. UI/fonts are assessed for actual scaling/filtering needs rather than excluded by category. Atlas, transparency and native layout work are compatibility tasks; source classification must advance into fixes and target qualification.

Use the efficient native format appropriate to colour count, alpha and sampling. Preserve compact palette encodings where suitable instead of converting every asset to 16-bit VQ. World/actor minification, effects/cutout edges and screen UI need their own quality checks.

Primary format references:

- [KallistiOS PVR texture formats](https://kos-docs.dreamcast.wiki/group__pvr__txr__fmts.html): pixel format, VQ compression and twiddled layout are distinct controls.
- [Dreamcast texconv author's documentation](https://github.com/tvspelsfreak/texconv/blob/master/readme.txt): native mipmapped textures must be square; stride textures cannot be mipmapped, twiddled or VQ. Palette VQ uses different codebook block dimensions. Rectangular adaptation requires explicit UV/wrap and per-level border handling.
- [Renesas SH7750 hardware manual](https://www.renesas.com/en/document/mah/sh7750-sh7750s-sh7750r-group-users-manual-hardware): CPU cache configuration for placement work.

Current package source: CAST_MIPMAP enables square16-bitVQ admission; new default-off TEX_TWIDDLED_MIPMAP and TEX_PAL4_MIPMAP extend native16-bit and compact PAL4 alpha admission. pvr_format forwards the mip bit through existing native_ui PVR headers. Actual Package sanitizer/decoder checks and disabled host-object identity are recorded, but full Dreamcast program identity, rendering, residency and hardware timing remain open. SH4ZAM skinning and texture mip selection are independent paths and are retained together in the eventual selected target.
