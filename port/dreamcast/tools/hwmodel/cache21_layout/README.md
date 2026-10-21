# SH-4 cache-layout proof of concept

This is the first analysis stage of a MipsFit-inspired SH-4 POC. It reads the existing RE4 hwtrace format and reproduces hwsim's instruction-fetch/cache convention. It does not generate a layout, relink a program or change game behavior.

The baseline gate passes on all 16 retained Oct18 r101-fast-a traces, frames 480..525 with stride 3: 158,164,423 instructions and 1,414,147 cache fills, exactly matching the pinned existing model. The [validation receipt](validation.json) records the actual ELF, replay source and every trace hash without distributing game data. This is the old model/scene, not a new Test21 or console result.

The same-size fully associative LRU reference classifies 10,582 first touches, 537,627 conflict misses and 865,938 capacity misses. These are diagnostic categories, not attainable savings. The largest recorded pair includes MeshDraw::run and lean::box_mask; both directions repeatedly evict a shared cache slot. Cache-line labels may overlap functions and do not establish movable input-section ownership.

Next steps are temporal placement using verified linker input sections, comparison with the accepted C3 order, actual relink verification and matched whole-frame testing. Reordering cannot be priced from aggregate miss counts alone. Preserve startup, vectors, overlays, literals/relocations and fixed sections. Reuse existing hwsim and ordgen_c3 rather than adding another timing model.

The SH-4 setup is 256 direct-mapped cache lines of 32 bytes and 2-byte instructions. Tests cover the 8 KiB conflict boundary, a halfword crossing a cache line, capacity/reference classification, P2 uncached fetches, malformed traces and ambiguous symbol labels.

Run tests with Python's unittest runner in this directory. The command-line tool takes an SH ELF, ordered --trace inputs, a new --out path, and optional --expect-fills / --expect-instructions baseline counts and --expect-elf-sha256 identity. The report records the replay tool's own hash. Input files are read-only; output overwrite is refused. Cache state carries across supplied files exactly as the inspected existing hwsim implementation does; that convention is not a claim about unknown real cache state between sparse samples.

References: [MipsFit33c02662](https://github.com/Byterset/MipsFit/tree/33c02662ed0a2143bbfc37d572ddae5afd537c62), existing port/dreamcast/tools/hwmodel and tools/d367/ordgen_c3.py. The approach is inspired by MipsFit's temporal/cache diagnostics; no upstream source code is copied. No performance improvement or release acceptance is claimed by this POC stage.
