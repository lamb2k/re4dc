# r226 full statue data — 2026-10-19 (H-036)

One full original cObjRobo model is prepared, preserving every source face and its complete 23-part owner. **The current game does not admit or draw it.** The registry refuses authored position shift 0. Typed ObjMgr ownership is a separate Performance P2 dependency.

No reduced level, runtime change, guard relaxation, recipe, game build, Flycast run, still sheet or production selection is included.

## Original room input

The inputs are original PS2 r226.dat, GC St2/r226.das and its decoded tagged room archive, pinned by the earlier statue source audit. The existing room_smd decoder was replayed in WSL and matches every decoded byte. A narrow source_room_archive adapter exposes the existing Archive entry API. It creates no new binary room format and does not disguise the statue as enemy em37.

Optional provenance fields apply only to explicit room sources. Each descriptor must agree on the room, source kind and original container. Hashes, bounds and ordinals are checked. Registry generation independently decodes the original DAS and verifies the relationship to the selected archive. Windows can use only an explicitly hash-pinned decoded cache.

Thirteen asset-free tests pass on Windows and WSL. Actual generator mutations of source kind, container hash and decoded archive all refuse before admission. The unchanged enemy path reproduces the approved r224 package exactly: `70a81b2638e9283f023958061490b55b61f03a609be312aff135fd5e75cdec03`.

## Complete source and native data

All 12,631 original PS2 triangles match the exchange and native oriented corner multiset, including duplicate multiplicities. Positions, numeric weights, UVs and material/image identities are preserved. Normals use the existing 14-bit quantization. All 23 joint parents, rest transforms and capture matrices are exact; unweighted joint 20 remains present.

Original positions are integer millimetres, bounded by [-5564, -1, -4067] and [5564, 23973, 4067]. The original GC BIN declares **position shift 0**. At that scale, native position error is 0 mm, UV error is 0 and original numeric weights are exact. Maximum normal component quantization error is 0.000030512131455.

The full native stream has 91 meshlets, 11,532 transformed records, 18,667 submitted indices, 3,018 strips, 54 palettes and 1,904 skin bytes. Header SHA256: `919a1d8c532cca74e4e5fc4d42859c83bdb31d99632c4e49b042b6e222313acf`.

All 12 material groups remain complete: 2206/724/1736/284/295/126/5216/172/568/42/1202/60 triangles. All 11 diffuse images are opaque. Interlace-1 images 1, 2 and 5 use the existing character transpose rule, consistent with GC display dimensions. Oriented source pixels and repeat-filter gutters match the uncompressed 1024×1024 atlas exactly. Source UVs remain unchanged; all source samplers repeat. No alpha classifier or cyclic-order tolerance is introduced.

The normal lossy VQ RGB565 representation uses 264,192 bytes of VRAM. Its 264,336-byte texture package has key `0806679c-68bc1c92` and SHA256 `27da88d61a94668788e77910540ce3eff99cf73c5b083c88d86b7973cadfedbf`. Encoded VQ pixels are not claimed source-exact. Actual GS, lighting, filtering and appearance remain unqualified. Inherited conservative/lean manifest labels alias the same full header; they are not additional geometry levels.

The converter at source 5647fc9c passes three synthetic host frames and 37,893 triangle checks with 512 KiB workspace, followed by exact strip VERIFY. Five actual coarse_actor_preflight.h controls pass under ASan/UBSan: the valid stream and invalid record, index, count and weight cases, with no sanitizer stderr. These establish packing and safety properties, not animated source poses, world-scale drawing, ownership or gameplay.

## Refusals and retained counterexample

The initial generic shift-2 attempt refused signed-16-bit overflow. Reading the original BIN established authored shift 0; using it preserves the integral source coordinates exactly. The final data records 0 explicitly. The current registry still refuses **`position_shift 0 outside 1..4`** and emits no registry.re4nmr. Descriptor low bits 0 already mean legacy shift 4, so loosening the guard would misinterpret scale. Neither encoding nor range was changed.

The converter's approximate triangle-centroid sampler reports a maximum surface value of 1100.626348 mm, with median and p95 zero. This raw result is retained. Independently, all 7,062 referenced GC/PS2 positions and every oriented position triangle are equal. Each point is an incident vertex of the other source mesh, giving exact point-to-source-surface distance 0. The approximate sampler is not a valid distance bound here. Material, weight and corner correspondence are proved separately.

The first Windows decode failed because its PPC compiler was unavailable. WSL replay then proved the exact original decode. Failed partial attempts and expected refusals remain private; none is treated as accepted data. Owned host executables and objects were pruned after retaining their results and hashes.

## Owner handoff and open gates

The coordinator routes these requirements to the existing character renderer/registry owner in Performance P2:

- Typed original ObjMgr cObjRobo id 0x37, type 0, 23 parts and one info: original live-list lifetime, preparation, texture facts, skin lease, OT0, postlude and visibility. H-034 shows this owner is absent from both the EmMgr ledger and the separate core/head object kinds. Actor-id substitution cannot establish ownership.
- A representation of authored shift 0 that preserves old descriptors' low-0-equals-4 behavior, source bounds, skinning, culling and world scale. A range-only relaxation is insufficient.
- The original room BIN 0x1f/TPL 0x20 lifetime, facts and lighting/material behavior. Switches, carrying, crushing, hands, feet, bridge and chase remain source-owned. No new room format is needed.

`boss18-r226-statue-full.json` is a preparation/refusal spec, not a complete room cast replacement. No arena fit is claimed without an emitted package. Native drawing, original animated poses, interactions, chase/death, whole-fight cost, residency, VRAM, 48 KiB KOS, STRICT/decisions, route and knob-off image gates remain open.

The native inventory estimate is 13.0669 ms using today's supplied slope. It is neither measured draw cost nor a complete-frame projection. Missing whole-fight remainder U prevents a new g50 decision under I-013.

## Private receipt

`boss18-statue-full-20261019` contains 160 files / 53,982,168 bytes. SHA256SUMS SHA256: `1df895179db17b9a327904b777b5a27d7b7972ad29a6d3c07a411950ab3247a2`. The immediate C mirror is byte-verified.

The set retains original inputs, one full export/native stream/texture, source and native proofs, negative controls, the default package control, failures and source snapshots. Public hash-only reference: `tools/d367/boss18/statue-full-source-20261019.json`. Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/statue-full-20261019/`.

No game bytes, generated header, texture or media enters Git. This handoff does not claim integration, release or overall boss completion.
