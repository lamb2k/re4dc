# Byte-neutral offline scenery dedup (SDO3)

Source/host evidence only. No target build, image identity, staged disc, Flycast
run, s30/KOS gate, console result, or production recipe change is established.

SCENERY_DEDUP=3 selects ps2-dd3.re4mesh and ps2-dd3.r4sg alternates. Default0
keeps the original filenames and original reader. Mode2 remains the SCDD room
section path with its existing load reorder. The offline converter reorders data
before play and stores repeat sources in the bytes already owned by each corner.
R4IM and R4SG file lengths do not grow; no source table, mask or dedup allocation
is added. Code/image growth and the resulting heap floor are still unmeasured.

## Format and admission

R4IM v3 prelit only. Header reserved[2] (offset72) is the original body CRC;
reserved[3] (offset76) is little endian 'SDO3' (0x334f4453). Current inputs have
zero in both words; the original reader has no use for them. All table offsets,
counts, bounds, palettes, classes, LOD and materials are retained. The body CRC
is recomputed. Each plain meshlet uses strip_count bits0..6 for its strip count
and bits7..14 for its repeat count. Bit15 still marks indexed meshlets, which
retain their full15-bit strip count. The converter rejects any input plain strip
count over127. Real r100/r101/r103 maxima are25/28/25.

Unique-position corners come first in their original order; repeats follow in
their original order. Each repeat stores (first_corner, 0x5344, 0x4f33) in XYZ,
retaining its own UV/colour. first_corner must be non-repeat; chains, bad tags,
out-of-range references and counts fail admission. Plain spans must be monotonic
and disjoint. For every part, one conservative interval bounds all indexed pool
accesses; overlapping plain spans are left unencoded. Existing ascending/disjoint
part-pool validation prevents cross-part aliases. This adds one linear part-local
pass, no all-meshlet pair scan, no scratch allocation and no retained mask.

At load, an alternate must match the base file size. A fresh80-byte standard-file
header binds its embedded original CRC to the actual standard package, then its
actual body CRC and structural reader validate it. Mode3 rejects unknown markers
and rejects marked data read under the standard filename. A missing alternate uses
the base. Knob0 ignores reserved header words as before; filename separation is
the isolation boundary. Its host test rejects these particular encoded packages
because their stored strip counts do not describe the baseline format, rather
than claiming an unconditional knob0 marker check.

R4SG group bounds and strip end offsets remain unchanged. Group corner ranges
become the first-source range needed by that group's strips. Every selected group
subset therefore primes its consumed repeats. The filler skips repeats whose
firsts were not transformed. The runtime validates all group boundaries and all
needed source ranges before publishing an alternate SG table; malformed SG data
falls back to the whole-meshlet path. R4SG authenticates actual encoded R4IM CRC/
size, retaining its original policy-sidecar CRC. The fresh base-header binding
allows existing rect21/interior/PVS source geometry identities to use source_crc;
actual bytes/fingerprints remain encoded identities. Optional SCCN/SCPS sections
still demand actual CRCs, so stale sections decline adoption safely.

## Coordinate and lifetime consumers

SCENERY_CHUNK already requires MESH_VP_SCHED=1, MESH_STRIP_LEAN=1 and !MESH_CLASSIFY,
so SCHED0/2/3 diagnostic paths cannot compile in a supported mode3 build. The fast
full path transforms firsts, then fills repeats with copied screen/depth/outcode
and each repeat's own UV/colour. Group subsets transform their rewritten source
span. Generic strips and every near/far/depth/oversize clip path pass through
Emitter::corner, which resolves XYZ from the current meshlet but retains own
UV/colour. The explicit classify-none/screen branches also avoid transforming
encoded XYZ. Indexed/unencoded fallback geometry retains its original bytes.

MeshDraw derives each source address from its current package. There are no
mode3 global table pointers, masks, generation records or extra heap allocations.
Only the Emitter's borrowed clip context adds12 bytes on a32-bit target; the source
header read uses an aligned96-byte temporary stack buffer. Actual compiler stack
and image layout remain target gates. Standard lighting/impostor functions read
different packages; only prelit PS2 world alternates are emitted/admitted here.

MeshPackage::close intentionally retains h_. Host tests verify this exact contract:
a movie close preserves the marker/source CRC, reread/adopt accepts the same stored
order, and adoption of the next ordinary package replaces the marker. Movie file
fingerprints use actual bytes; reload chooses the retained alternate filename and
refreshes the already stored order without a reorder or allocation. Real room
retirement retains no mode3 borrowed pointer.

## Host results at base451bed6f

Inputs: t164-20261018 payload R4IM and r101 R4SG. Current recipe sidecars resolve to
mip22b-20261022 and are retained. These are loaded-package counts including unused
LOD/fallback, not a camera sample or frame-time result.

| Room | Corners | Encoded repeats | Encoded meshlets | Indexed fallback | Pool-overlap fallback | R4IM bytes |
|---|---:|---:|---:|---:|---:|---:|
| r100 |108869|14490|1127|43|94|1537920|
| r101 |93576|10277|756|227|563|1283520|
| r103 |79169|12915|759|146|351|1074688|

r101 R4SG remains117152 bytes. r100/r103 have no R4SG in this input recipe.
Six Python tests cover seams, group priming, unknown/malformed references, stale
identity/CRC, equal-size foreign source and repeat chains. The real C++ reader
admits all3 encoded packages with0 new allocations and preserves every ordered
six-word strip corner:123664/103562/85192 respectively. It rejects malformed
marker/source/tag/count and invalid SG ranges. All3 pass full Python ordered-
corner comparison; r101 passes every SG source-range check too. Host tests are
not evidence of target instruction correctness, image identity or console speed.

Private evidence: C:/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/.
The current conservative variants are r100-linear, r101-linear and r103-linear;
the earlier *-prototype outputs used a superseded exact-overlap ownership proof.
Private data is never committed. No alternate has been staged into a disc.