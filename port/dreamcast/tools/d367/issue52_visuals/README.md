# Issue 52 material binding diagnostic

`audit.py` reads an explicitly selected little-endian source archive, source-coverage receipt and texture pack. It binds each requested BIN/TPL pair by exact archive SHA and original image index, follows `ModelPart.flags & 4` through the source mask, computes the existing `R4MPv001` pair key and records the selected member SHA and descriptor. Ambiguous/missing source indices and unequal colour/mask dimensions fail explicitly. Outputs must be new files.

Example: `python3 audit.py --archive private/r117.arc --coverage private/coverage.json --pack private/selected.pak --model 0x1f:0x20 --out private/result.json`.

This is read-only source/asset diagnosis. A supplied subset pack proves only its recorded members; it does not establish a full-pack hash, runtime alias selection, submission, appearance, performance or physical Dreamcast acceptance. No renderer or release switch changes.

Tests: `python3 -m unittest discover -s port/dreamcast/tests -p test_issue52_material_bindings.py -v`.

## Opt-in lake floating-island candidate

`repair_lake_bark.py` fixes the reviewed r10b room BIN0x1e texture-index mismatch. PS2 image2 is bark and image3 is the stump; their retained GC materials are images4 and5. The original conversion placed406 bark triangles in the GC branch material (flags4, alpha mask3), leaving the opaque bark part empty. The exact original conversion reproduces the selected public BIN bytes.

The candidate calls the existing converter with map `{0:0, 2:4, 3:5}`. It requires the exact reviewed public Test21 DAR and exact original GC/PS2 BIN SHA256s, checks all529 triangles and retained material contracts, and verifies unrelated payload entries are unchanged. TPL/package keys and program bytes stay outside the repair. Output is disabled without `--enable-r10b-bark-map`; no staging recipe or default changes.

Example: `python3 repair_lake_bark.py --dar private/public-r10b.dar --gc-bin private/gc-1e.bin --ps2-bin private/ps2-1e.bin --out private/candidate/r10b.dar --report private/candidate/repair.json --enable-r10b-bark-map`.

Source validation produced candidate DAR SHA256 `8c84649bc5fc87a1b78336349e4ae8e9607440a48f90296458895bebb3db8566`, unchanged5808128B, with5079 changed bytes confined to BIN0x1e. Repaired Flycast appearance and physical Dreamcast acceptance remain open. Evidence/source receipts live in the private issue52-visuals-20261021 folder.

## Opt-in officer head material candidates

`repair_officer_heads.py` repairs two exact Test21 r100 head BINs. The first PS2 face image0 corresponds to GC image2; the second PS2 face image4 corresponds to GC image6. Index-identity assignment instead selected the small blank/hair materials. Existing conversion reproduces both selected broken BINs exactly. Explicit source maps retain all1021/1276 triangles, positions, normals, UVs, colours and weights; only their material cohorts change. Each BIN is padded to its existing extent, preserving DAR/heap/ISO offsets and texture/NTR records.

Example: `python3 repair_officer_heads.py --dar private/public-r100.dar --sources private/dynamic-source-exact02 --out private/heads/r100.dar --report private/heads/repair.json --enable-officer-head-map`.

Candidate DAR SHA256 `bdfbba1837d5cd3efcc8ba64d63955abf90819cb375d6d9f1e378bec1f7e2e36` has unchanged5373952B. Exact-input guards and the explicit enable flag apply. Officer body atlas/UV layout remains a separate open case; this candidate does not establish a complete officer repair or a repaired target appearance.

The church swinging chandelier is also separate: three PS2 pictures/UV spaces were merged into the retained single GC atlas. An index-map alone cannot repair that layout. Retained source proof records the1270-triangle material split (1046 opaque,40 curved fixture,184 chain); no chandelier candidate is enabled here.
## Opt-in chandelier atlas candidate

`repair_chandelier_atlas.py` repairs the exact public Test21 r117 chandelier (BIN0x1f / TPL0x20). It packs the three original PS2 pictures without resizing and rebases each source material's UVs. The opaque body keeps alpha255; the chain and curved fixture retain their separate masks and all16 intensity levels. Eight-texel periodic collars preserve the retained source colour/mask REPEAT modes at UV seams. One original material remains one material; the source joint, animation, lighting and blend contracts stay intact.

Example: `python3 repair_chandelier_atlas.py --dar private/public-r117.dar --sources private/dynamic-source-exact02 --out private/chandelier-atlas --enable-chandelier-atlas`.

The tool is disabled unless explicitly enabled, checks the exact DAR plus four original source identities, and refuses an existing output directory. It writes one candidate DAR, three loose texture packages, a source atlas preview and a receipt. It does not edit or invoke a production recipe. All1270 oriented triangles retain their positions, normals, colours and weights. The26912B BIN extent stays fixed: the rebuilt26848B BIN receives64B padding. Only this BIN and two8B native texture keys change; room size, NTR table, TPL descriptors, object placement and every other room byte stay identical.

Host qualification: eight source tests pass;8890 bilinear samples match the separate source pictures within floating-point rounding; native package alpha decodes exactly to the16 source levels. Repeated WSL and Windows Python generation produces identical DAR/packages. The legacy signed8.8 UV representation adds up to0.4981 atlas texel of coordinate error, so target appearance remains a required gate.

The pair is native ARGB4444,131072B of texture payload versus the old VQ pair18432B: **+112640B source residency payload**. There are90 unique ARGB4444 words but1968 distinct2x2 blocks, so a single256-entry VQ codebook cannot encode it exactly. This correctness candidate adds no palette/runtime switch; target texture capacity and appearance remain open. No speed benefit is claimed.

Candidate DAR SHA256: `94b8b3b81e8fa80cd8dfd6f1ed0970cc21b3d1eed9a3dfef5fb6e8a10540de6e`; unchanged4149248B. Pair key: `9699ee7e-5b272575`. Exact receipts, private assets and the queued target plan are in `issue52-visuals-20261021/chandelier-atlas-candidate01`. No build, stage, guest, release or physical Dreamcast acceptance ran. Officer body work stays separate.