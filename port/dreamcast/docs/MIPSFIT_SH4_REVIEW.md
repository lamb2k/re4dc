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

## Textures: compatibility using native formats by family

Mipmap generation now has an implementation owner. Begin with an opt-in lower-level mip generator for existing square 16-bit VQ world textures; preserve original base indices/codebook and existing output when off. The first private candidate is the farm's 15 compatible keys, whose source-counted extra payload is 16,394 B. Actual allocation overhead and concurrent VRAM are separate gates. Continue through palette, rectangular/atlas, alpha and renderer-consumer contracts after this first path.

Use the efficient native format appropriate to colour count, alpha and sampling. Preserve compact palette encodings where suitable instead of converting every asset to 16-bit VQ. World/actor minification, effects/cutout edges and screen UI need their own quality checks.

Primary format references:

- [KallistiOS PVR texture formats](https://kos-docs.dreamcast.wiki/group__pvr__txr__fmts.html): pixel format, VQ compression and twiddled layout are distinct controls.
- [Dreamcast texconv author's documentation](https://github.com/tvspelsfreak/texconv/blob/master/readme.txt): native mipmapped textures must be square; stride textures cannot be mipmapped, twiddled or VQ. Palette VQ uses different codebook block dimensions. Rectangular adaptation requires explicit UV/wrap and per-level border handling.
- [Renesas SH7750 hardware manual](https://www.renesas.com/en/document/mah/sh7750-sh7750s-sh7750r-group-users-manual-hardware): CPU cache configuration for placement work.

Current package-source check: CAST_MIPMAP enables square 16-bit VQ admission in room/texture_package.cpp; pvr_format forwards the mip bit to ordinary native_ui PVR header consumers. Palette branches omit that bit and their admission excludes mips. Those are concrete compatibility tasks for the next family, not proof every consumer works. Source inspection is not a rendered or final hardware certificate.
