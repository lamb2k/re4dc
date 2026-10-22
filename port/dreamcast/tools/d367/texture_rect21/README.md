# Rectangular native-world adaptation

Current acceptance boundary: staged C proves texture admission only. The audit
found whole-R4PW checksum dependencies missed by the earlier byte-level image
gate: C rejects dynamic IDs, transparency classes and the r100 interior
fingerprint. Preserve those captures; they do not establish gameplay or
comparison equivalence. `coupled-behavior-qualification.json` records the defect,
original-four provenance and guarded repair proposal. Originals remain and
WORLD_RECT21 stays default0. The following entries retain the work history.

The first main-lane step recovers existing native bindings before changing layouts. `world_bindings.py` consumes an exact 29-world candidate receipt and the 792-key main queue, verifies every R4PW body checksum and input SHA, then joins actual material-part bindings to logical texture dimensions. It never changes textures, geometry, UVs, runtime or a release.

2026-10-21: all 29 sidecars read from current QA aafc10f3 match the selected original inputs exactly. All 792 rectangular keys have exact native bindings, across 4,371 part rows. Evidence: `C:/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/native-bindings-01/bindings.json`. Missing references in the older generic TPL probe therefore do not mean these native texture consumers are unidentified.

Current `native_ui.cpp` world packet paths reject width/height differences, select bilinear repeat sampling, and return UV scales of 1. `native_ps2_world.cpp` has separate legacy/source-owner and kernel paths. The square-adaptation candidate must preserve periodic sampling and update every actual vertex consumer; dropping the dimension guard alone is incorrect. Existing original TPL wrap behavior and current native presentation are distinct contracts. Atlas material domains are a separate task.

Next: prepare the first farm/woods rectangular cohort with a sampling oracle and exact base preservation, account for repeated square storage versus compact formats, and qualify opt-in runtime bindings before combining. No converted rectangular package, target timing or rendered acceptance is claimed yet.
First offline prototype: r103 key1c7a6886-9dcfa8d2,128x64 VQ to a repeated128-square representation, followed by existing mip generation. Original decoded pixels and the codebook are exact. The independently compiled pinned pvrtex decoder verifies the original rectangle, square and all eight levels. Bilinear repeat sampling agrees at2097 negative/positive/edge coordinates with UV scale(1,0.5), maximum channel error0; deliberately omitted UV scaling fails2062 cases. OFF returns the original bytes. Private images are visually inspected.

This demonstrates a source-compatible base representation, not an accepted runtime texture. Payload grows4096→6144B before mips and7510B with mips; lower levels remain intentionally filtered/quantized. Runtime dimension/UV changes, lower-level appearance and target resource/performance gates remain open. The prototype is not composed into the texture pack. First oracle compile failed on unused palette image-loader symbols; the working build exports only decoder gates and drops unused sections with a strict no-undefined link. Failed outputs are preserved separately.

The resumed farm/woods unit adds `cohort.py` and `compact.py`. The first seals 19 original 128x64 VQ keys in r100/r103 as repeated 128-square mips. All bases/codebooks stay exact; rounded requests grow 77,824 to 142,880 bytes. Blanket conversion of all 672 compatible rectangles would grow 5,171,200 to 14,310,400 rounded bytes, so it is not adopted. The 120 other layouts remain held.

The alternative is an explicitly approximate shorter-side 64-square representation for 17 opaque RGB565 keys. It filters the horizontal axis and requantizes against the unchanged original codebook, then adds mips. Rounded requests fall 69,632 to 58,208 bytes; full-resolution base pixels change. Two alpha-format keys remain held. Normalized UVs remain `(1,1)`, while repeated-square needs `(1,0.5)`. Inferring UV scale from physical dimensions would therefore be incorrect for the approximation. Offline contact sheets were inspected, but scene look and performance remain unaccepted.

The initial 7099b9140 version of `world_rect_bind.h` admitted the 36 key/logical-shape/physical-descriptor/CRC combinations from these alternatives. They are now retained only as held offline evidence; the active source admits the scoped 17 keys described below. It defaults disabled and changes neither scale on any rejection. `WORLD_RECT21=1` installs it only in `re4dc_ps2_world_direct_begin`, with identical cached and cold descriptor gates. A cached header must also match the current physical TSP extent, so an Entry/address reused by the other representation rebuilds its header. The make knob defaults to zero, rejects invalid values, and requires PS2_WORLD_DRAW, PS2_WORLD_MESH and MESH_DIRECT. No production recipe enables it.

Actual native_static mesh and chunk consumers set direct=true, copy both returned packet scales, and apply them in direct/clipped emission and fast-kernel constants. The separate legacy native_ps2_world packet/kernel emitters copy unscaled UVs; all of their original dimension guards stay intact. Generic model, actor and UI paths receive no new admission. A combined texture pack must still close any alias consumers before target use.

Source gates: 271 independently decoded levels; 36 actual native Package host-reader passes under ASan/UBSan (all rejected with mip support disabled); 36 adapter admissions, 468 disabled/mutated descriptor refusals, and 112 cached-extent checks. The original legacy data-only CRC convention passes the streamed Package path while the memory path rejects it, exactly as before. Actual SH-4 native_ui preprocessing and complete object bytes are identical between f0fd510b7 control and the changed source with WORLD_RECT21=0. ON changes the object; before linker collection it adds 404 text and 1,872 rodata bytes, with no data/BSS growth. Default/explicit-zero make compiler commands remain identical to the old command; ON adds only the selected define. This is source/host/object evidence, not a full program, Flycast, release or physical Dreamcast gate.

Exact source/asset/object identities are in `farm-woods-qualification.json` and `knob-qualification.json`. Private candidates, receipts and contact sheets are mirrored under `re4-assets-private/texture-rect21-farm-woods-20261021`; no combined pack has been composed. Evidence remains under `C:/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021`.

The scoped fixture is now generated and qualified using `scoped_candidate.py`. It derives 17 immutable candidate key pairs, excludes all original/loose and both reserved atlas key pairs, appends packages using the existing texpack format, and rewrites only selected key words plus R4PW body CRCs in private r100/r103 copies. All 6,501 original pack members remain byte-exact; the resulting 6,518-member archive grows by 69,632 bytes. Only the scoped 17 allowlist is active. All 36 original-key experimental representations are refused by the updated adapter, so unknown generic aliases keep their exact original packages.

Four focused transformation tests pass; the scoped fixture's 119 levels independently decode; all 17 exact files pass the actual native Package host reader under ASan/UBSan. The updated adapter passes 17 admissions, 221 invalid/disabled refusals, 36 held-original refusals and 55 cached-extent checks. Actual full SH-4 native_ui TU/object disabled identity still passes. The scoped-only ON object adds 404 text and 884 rodata bytes before linker collection, with no data/BSS growth.

The original disk-floor refusal is preserved. Generation subsequently passed after root reclaimed space; the finished set is mirrored and hash-verified at `re4-assets-private/texture-rect21-scoped17-20261021`. Candidate pack SHA256 is `e4fb6975831e8a226a6d733ce4d6ba4979eca7ef2dd1ba37aa6ee50eaf0f2c30`; the full input/output/source/sidecar identities are in `scoped-qualification.json`. SHA256SUMS is `d5c3b44308dd4b4223ad6589f04862e5a4374a22cf6cc37f69f468ed73896a79`. No full game build, disc staging, guest, scene look, frame-time result, release or physical Dreamcast acceptance has been run. Selected texture requests shrink 11,424 bytes while the archive grows; if originals also load, combined rounded requests could be 127,840 bytes. Actual combined peak remains open.

`integration_manifest.py` prepares a read-only exact combination receipt for a chosen base pack. It checks that all original keys remain, the selected 17 source rectangles are still exact, and scoped IDs do not collide, then verifies expected combined bytes in memory without writing a pack or staging files. It preserves every selected-base member, including inherited changes. With the frozen 947-mip candidate (pack ba40722d...), the expected 6,518-member result is e824af055d12d9e145ae5448c3dfd77b7e8e2943f0c7e8d23bd6caf9d4dc23e6, preserving all 1,076 inherited changes and growing the archive by 69,632 bytes. The standalone scoped pack is based on original textures; installing it over another selected texture candidate would discard that candidate's work. Main retains integration/build ownership.

The current selected integration input is now the sealed **948-mip** pack e19cfc464e789e97ca96864adfc2a4cd44443a9f4775bebd842c3e184a65559b. A fresh read-only receipt preserves all 6,501 base members and 1,077 inherited changes, explicitly protects masked Efm key 6da8c35b-a936da0c, and appends scoped 17. Expected combined SHA256 is bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026. The 947 receipt is retained as historical evidence. No new combined pack was written; root still owns the final input freeze.

`room_cohort.py` prepares a separate held r101 cohort. Nine opaque 256x128 original VQ files filter to 128-square mip chains, keeping original codebooks. All 72 levels independently decode, and nine actual Package sanitizer cases pass (all reject with mip support disabled). Rounded texture requests would change 92,160 to 67,680 bytes. The offline contact sheet was inspected; this is a visible approximation with no scene approval. No scoped IDs are allocated and no active table, frozen scoped-17 file or pack changes. Full-resolution evidence is mirrored under `texture-rect21-r101-held9-20261021`, SHA256SUMS 202346008e0030717e1db562aa5aeac13935cf142c4a5e8eb4ec7fb2a7d6b5fa.

Source consumer review confirms PS2_PRELOAD_LEAN reads the scoped keys from the current R4PW, while source archive scenery preload is skipped. Object first-sight and other archive consumers remain independent, so this does not prove originals absent from runtime residency. `preload_least` still uses logical shapes and estimates 4,096 bytes for each scoped-17 texture versus its 3,414-byte payload; selection conservatively overbooks 682 bytes/key. No preload/cache edit is made here, and actual target residency remains open.

2026-10-21: the frozen 948-mip plus scoped-17 combination is now materialized as a data overlay and mirrored exactly, without a game build or staging. Pack bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026 is 155,856,896 bytes, including all 6,501 selected-base members byte-exact, all 1,077 inherited changes and only 17 appended scoped keys. There are 965 mip keys. Both R4PW files are the exact frozen scoped copies; all logical/material fields and placement bytes remain unchanged. Atlas two and held r101 nine remain outside this overlay.

The set is `/root/re4data/private/texture-rect21-current948-scoped17-20261021`, mirrored at the same basename under the C: private assets folder. SHA256SUMS is b2dc69e1d1ee705ded6604b13f0649313c69378ac09f7945035c4ada95e1cfbe. An independent raw header/index parser verifies all 6,518 member hashes and base byte equality; direct stream comparison verifies all six files and exact directories between WSL and Windows. Public `current948-data-qualification.json` records the full data/source identities and required inherited format flags, while private membership-proof.json retains every member hash.

Actual data plus mirror writes are 317,081,742 bytes, exactly as forecast. Including producer and review evidence, the completed data output uses 317,098,792 bytes of the 536,870,912-byte allocation. Fresh-start 18 GiB plus 768 MiB and runtime 18 GiB plus 64 MiB guards passed; no third pack copy was written. The observed host free-space delta is recorded separately and is not an attributed write cost or performance result. `materialize_current948.py` preserves prior output paths and refuses before output if measured bytes, allocation or headroom fail. Main separately owns the exact matching guarded source/program freeze and all target gates; this data artifact is not program, scene, timing, release or physical Dreamcast acceptance.

2026-10-21 full program qualification: frozen runtime source
`004cf224674fa60cf08dc10e641c723de238a0fd`, original QA8942 recipe
`54d2e5d56f84d76c5c0071484771ca74957c6649d28b103a5974943728715f70`.
OFF raw program `8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d`,
all14 overlays and ELF load segments match the original control exactly. ON raw
program `a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71`
links with required mip/PAL/world flags explicit; all14 outputs are retained.
Atlas runtime hooks are absent from this frozen source and both atlas keys stay
excluded. This qualifies source compatibility with frozen948+17 DATA pack
`bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026`.

`program-qualification.json` records exact source/program/asset identities and
static costs. ON adds1984 text,896 read-only and2112 BSS bytes, data unchanged;
linked `_end` advances5120 bytes after alignment. Direct-world bind frame360→384
bytes plus40-byte helper; PAL planning frame480 bytes. Compiler stack observers
are stripped-object exact to actual build objects. These per-function numbers
are not runtime stack/heap high-water or target performance. No image staging,
guest, scene look/residency/regression or physical-console acceptance occurred.

2026-10-21 standalone image and cold-test plan (`image-qualification-plan.json`):
read-only verification rehashes all 1,743 baseline files, every file extent and
1,874 ISO/Rock Ridge directory records. This exact baseline has no Joliet tree.
The PVD declares 504,000 sectors while track03 contains 504,150. All 150 decoded
tail sectors are zero and outside every file/directory. The enlarged final
program needs two of them: keep its original LBA 547365 and every other file
extent, expand the volume count to 504002 and preserve the remaining 148 tail
sectors. Both packs, all overlays and sidecars fit their original allocations.

A future single-pass raw2352 to cooked2048 writer changes only selected payloads,
zero padding and exactly three metadata fields: program size, pack size and
PVD volume count, each LE/BE pair. The selected allowlist is program,14 overlays,
pack,two sidecars. B changes16 files; C changes18. All1,725 unrelated file extents,
lengths and hashes stay fixed. No new directory tree, whole extraction or
intermediate image is needed. Stage readback must verify every file plus the
exact metadata delta and retained tail; a virtual hash is not an image test.

Each cooked track stays 1,032,499,200 bytes. Conservative full-image bounds are
1,034,794,967 bytes per image and 2,069,589,934 per pair; with16MiB metadata reserve,
the pair bound is2,086,367,150 bytes, below2.3GiB. `plan_image.py --out <new-dir>`
creates metadata only. Streaming RAM-only overlays predict B track SHA e9efca15
and C SHA13c99813; future staging must match the full digests in the receipt.
No image was staged and no guest ran. Earlier append plan03 is superseded.

Cold-plan evidence maps17 scoped keys onto49 r100 and29 r103 material rows. Each
B/C image needs its own new cold checkpoint lineage; no original-image save can
transfer. Same ON a58579b8 B/C comparison isolates17 rectangles from the inherited
948 pipeline. Read-only resident/cache fields and stable observed SQ-header
snapshots can establish distinct minimum admission/submission evidence, with
explicit visibility limits. Approximation look, actual key coverage, co-resident
originals,lifecycle and matching benchmark windows remain target gates.

2026-10-21 stage readback: authorized sequential C then B images now exist under
C evidence standalone-C-01/gdemu and standalone-B-01/gdemu. Both match their
RAM-only predicted complete cooked hashes, including source program and all14
overlays. An independent directory/byte reader verifies all1743 file extents,
18C/16B actual changed members,1874 directory records,three LE/BE metadata field
pairs,PVD504002,IP.BIN,TOC/GDI/othertrack identities and148 retained zero sectors.
The original program LBA is retained. No fulltrack mirror,full extraction or
intermediate image was created. `staged-image-qualification.json` binds this
image gate to frozen004cf224,a58579b8/e08c9abc and their exact DATA inputs.
A single fresh C functional guest is allocated next; B timing is not allocated.
2026-10-21 C cold functional check (`cold-functional-qualification.json`): one
fresh ordinary QA r103f guest ran41.9095005 seconds, within47.5 absolute/41 inner,
with15,529,812 maximum capture bytes,no foreign state or checkpoint save/load.
It cold-booted,entered the farm and rendered the inspected t0037 view with terrain,
hut/tree and HUD. The t0031 pair is still a loading transition; retain both.
All9 farm scoped keys have contiguous named load,VQ3414-byte payload and upload
success records with measured3424-byte allocation deltas each(30,816 cumulative).
These are upload observations,not steady residency,savings or per-key draw proof.
Sampled aggregate counters report native48+9 parts,fallback/aborts0,UI missing0,
VRAM retries/rejects/evictions0. No matched B guest or performance attribution.

The typed observer confirmed exact program anchors then failed on missing
`room_id`: its DWARF parser omitted a promoted anonymous union/struct field.
The original source/output/failure and a subsequent unavailable same-PID attach
attempt are preserved. This is an observer defect,not evidence of a game crash.
The benchmark owner fixed and source-qualified the parser after C01; no second
guest is inferred. Live residency/co-resident originals,per-key SQ witnesses,
camera/tick bindings,all8 woods keys,lifecycle checks and physical acceptance
remain open. Qualitative historical-A image inspection has no measured camera
or source-tick equality and cannot establish exact look acceptance.
C02 and C03 are separate, explicitly allocated cold guests; neither overwrites C01.
`cold-functional02-qualification.json` records nine farm candidate descriptors,
owned known VRAM bases and simultaneous residency. Its controller-camera view
and projection arrays were zero; those are not active render-camera evidence.
`cold-functional03-qualification.json` uses observer runtime03 SHA694b31d3 to
read active `pG->Cam` and the controller separately. Active camera matrices and
projection are finite/nonzero, and complete gameMainLoop-only PT windows241–300
and301–360 plus the farm screenshot establish postload gameplay. All120 source
ticks241–360 were captured. Direct Rno0/Stop phase flags were not sampled.

C03 has80 coherent selected tables,66 with all9 exact64x64 RGB565/VQ/mip keys on
nine owned known bases. Payload30,726B and rounded request30,816B are lower
bounds, not full allocator extents or high water. One stable minimum SQ header
witness identifies00bdfb7c-15425fe6 at source/UI399, physical64square/VQ/mip,
with its known VRAM base. It does not establish all-key draws, vertex/raster
work, sampled pixels or exact look approval. Full-resolution captures and
C01/C02 failures/limits remain intact. The conditional same-program B control
must pass actual camera/player/health/source/control and counter comparison
before any matched timing statement. These are Flycast proxy observations;
release checks and physical Dreamcast acceptance remain separate.

The conditional B01 control completed42.0804155 seconds,16,789,535 maximum
capture bytes, with fresh userdata and the same a585/e08 program/observer.
`matched-farm-qualification.json` binds independent original-pack descriptors:
nine128x64 RGB565/VQ4096 no-mip originals are live on owned known bases in66
coherent B tables. C uses the corresponding nine64x64 mip/VQ3414 candidates.
Strict comparison fails47/120 source-tick pose/camera sets in the predeclared
241–360 window; boundaries241/300 differ,301/360 match. Those later matching
boundaries do not replace the rejected comparison. No speedup or paired timing
delta is reported. Sampled disc counters stay constant240→360 in each arm,
but source-frame coherence is not a completed-state phase latch. The benchmark
lane owns that next source-only audit. Both staged image hashes are unchanged.

`woods-functional-qualification.json` closes the allocated cold C house check:
all8 r100 scoped candidates are admitted on8 distinct owned known bases, in87
coherent tables. Together with farm C03, all17 selected candidates now have
actual admission evidence across two distinct scenes, not all-key final draw
acceptance. Active HOUSE AFTERS20 gameplay is confirmed by full gameMainLoop
PT windows,367 active-camera samples and the inspected interior screenshot.
The historical natural-start woods1801–1920 benchmark is a different scene.

Four original r100 keys remain co-resident:1170b2b5-9710ab82,
1ab5c10f-d8d37c49,24b92cf4-ddafaf29,5cbedd66-ce488718. Their actual C-pack
CRC/material/offset/descriptors match, each128x64/no-mip/VQ4096. All8 candidates
plus4 originals occupy12 known owned bases in87 coherent tables.43,696 payload
bytes and43,776 rounded-request bytes are lower bounds, not full allocator
extents, high water or net savings. Generic alias/preload provenance remains
open; no originals are removed and WORLD_RECT21 remains default0.

Eight stable minimum SQ-header events cover only3 unique candidates. Their
64square/VQ/mip headers bind to the observed known bases; vertex/raster/pixel
use for all8 is unproven. Source ticks equal observed UI frames+5 in these
events; both clocks are retained, and the old observer did not read the actual
skip counter or a completed-state latch. Two cross-tick table rows and4 torn
selected entries are excluded. An initial postprocessor field-name error
(reserved versus actual reserved_0) is preserved with its corrected analysis;
the frozen observer, program and raw guest are unchanged. No additional guest,
traversal extension, timing gain, release or physical Dreamcast acceptance.

`coupled_sidecars.py` is a pure byte preparer for exactly two dependent gates:
R4ID CRC bytes12–15 and R4TC binding bytes16–19. It requires pinned original
sidecars, byte-identical pinned geometry and placements, unchanged logical
material/pass/alpha fields, exact immutable selected package SHA/layout/CRC,
unchanged other package bytes and valid original class semantics. It returns
proposed bytes and hashes; it never writes assets. `audit_coupled_sidecars.py`
reads frozen B/C inputs and writes JSON only.18 mutation/control tests pass on
Linux, optimized Python and Windows, including valid texture slot0, exact
identical-world control and rejection of changed geometry/material/placements,
classes, mappings and package identities. No full image or asset is generated.

The actual78 changed rows are45 r100 opaque plus4 vertex-alpha rows, and29 r103
opaque rows. All selected texture formats are RGB565 with alpha1; vertex-alpha
flags/colors, mesh and placement bytes stay exact. The classifier actions are
therefore unchanged relative to B. This does not certify every inherited948
mipmap/classifier path. PCL1/runtime interior constants and OCCL consumers remain
separate, and the preparer always reports full_equivalence=false. Main owns the
coherent integration decision; this module is not a runtime fingerprint bypass.

Four old keys are selected directly by resident.bin room100 rows13,21,23,46.
They do not appear in the active DAR146 or scenery ARC100 identity rows, current
R4PW, typed19 native room/mesh inventories, or registry target/source texture
facts. Their observed entry UI frame remains181 after source241. This explains
current conservative preload overlap; it does not prove global nonuse across
core/enemy/weapon/inventory/future routes, so originals remain available and no
removal is proposed. No net savings, speedup, release or hardware acceptance.
