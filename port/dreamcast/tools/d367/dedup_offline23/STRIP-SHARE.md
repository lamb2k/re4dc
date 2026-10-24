# SDO3 exact strip-block sharing

The fresh5be full-H2 pair still failed the ordinary memory floor: OFF98,016,
ON93,920 despite the562-byte unit repair (fresh linked saving576). mem.cpp fits
`(room-(196608+64))` down to4KiB; it does not round absolute `_end`. Root's
measured remaining room loss was2,496 bytes, with only568 bytes of OFF slack.
No allocator reserve, floor, recipe, linker, or unrelated feature is changed.

## Exact data opportunity

Every global vertex and every local strip corner is referenced in all three
actual packages. There is no unused vertex span to remove. Section gaps total
only137/177/129 bytes. However, many meshlets have byte-identical full strip
blocks. These include the entire u16 pool-offset table for indexed meshlets,
followed by exactly the existing strip bytes. The packer stores each distinct
block once at a2-byte aligned offset and points identical first_strip fields to
it. Every index byte, strip order, winding, vertex, UV/color, bounds, LOD, mesh,
part, source ID and placement is retained.

| Room | Original file | Compact file | Allocation saving | Duplicate blocks |
|---|---:|---:|---:|---:|
|r100|1537920|1488192|49728|682|
|r101|1283520|1243808|39712|622|
|r103|1074688|1047968|26720|391|

Inputs remain the original four frozen `*-linear` files. New private files are
in distinct `r100-stripshare-v1`, `r101-stripshare-v1`, `r103-stripshare-v1`
directories under `C:/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023`.
Only r101 has an alternate R4SG. Literal paths and all hashes are in
`strip-share-private-pins.json`. No staging, programme build, guest, production
asset overwrite, release or SD action ran in this lane.

`strip_share.py` accepts only prelit R4IMv3 SDO3. It preserves the prefix through
the vertex array, packs strips, and moves the entire unchanged palette/LOD tail
to its next32-byte boundary. Classes, rules and extra runtime tables must all
be absent; unsupported layouts fail. Header counts remain unchanged. It patches
first_strip, strip_bytes, physical bytes/bodyCRC, palette offset and all three
present absolute LOD offsets. Validator checks those offset deltas explicitly,
not merely tail-byte equality. A CRC-recomputed wrong part-LOD pointer is a
negative control. The R4SG body is byte-identical; its header binds new actual
package CRC/size while its policy and body CRC remain unchanged.

## Source identity versus physical storage

SDO3 header reserved[1] (word17) now records the original baseline byte extent
for compact files. All actual baseline/prelit input word17 values are zero.
This word cannot be an oct-vertex table because SDO3 admission requires prelit
ARGB1555 and version3. A nonzero source extent below physical bytes is refused.
`source_bytes()` resolves nonzero SDO3 word17, otherwise actual bytes; legacy
byte-neutral SDO3 remains accepted. There is no new object field, heap block,
mask, reset or retained runtime state.

Initial open still reads the actual baseline80-byte header. It verifies its
magic/version, declared bytes against the actual baseline descriptor, prelit
encoding and zero source/marker/table words. The alternate physical size must
be112..baseline-size. Before publication, the resolved original extent and
original body CRC must match the fresh baseline certificate exactly. Alternate
own header.bytes, all section/range/ref validators and own body CRC remain
physical checks. A compact word17 of zero therefore fails the fresh certificate;
a small, oversized or foreign extent cannot relax it.

Only the semantic source-CRC/byte pairings for rect21 provenance, PVS and PCCULL
use source_bytes. Immutable provenance tuples are unchanged. Allocation, I/O,
new SG own package-size binding, sidecar storage and movie snapshots all retain
actual compact bytes. Other color encodings/readers are not relaxed.

## Consumers and movie lifetime

The actual mode3 reader validates each aliased strip/table span independently.
All mode3 consumers read those bytes; the in-place strip writes belong only to
excluded modes1/2. Relative SG endpoints and source spans still name the same
unchanged byte sequence, including clip/subset seams. Vertex/pool ownership and
source-first priming are unchanged.

The r100 movie layout has an additional mode3-only exact compact branch:
mesh1488192, side19612, total capacity1512928, retained marker and original
source extent1537920. The original baseline/full-SDO3 branch is retained. The
existing movie ledger captures actual compact file sizes and whole-file
CRC/FNV; close retains h_, the same alternate filename is reloaded, and both
whole-file hashes plus current room generation/cell validate before reuse.
No generic size allowance replaces those lifetime proofs. Root's prior movie
used363360 bytes; the smaller loan still needs an actual full-H2 gate.

## Host evidence and limits

20 Python tests pass. Actual C++ reader passes both legacy and compact variants
for all3 rooms, comparing123664/103562/85192 ordered corners against original
baseline. It checks no reader operator-new, source extent retention through
close/re-adopt, malformed replacement after success, ordinary rebind, invalid
extent, repeat references/tags/counts and r101 SG records.

`check_strip_binding.py` extracts the actual fresh-open header-selection block,
alternate source/body-CRC block, movie-layout predicate, and CRC/FNV functions.
Mock I/O controls pass for all3 rooms: legacy/compact positives; zero/small/
oversized/foreign extents; wrong baseline CRC/length/encoding; alternate own
size/body-CRC/truncation negatives. The r100 control checks close/retained-header
layout, wrong mesh/side/capacity, ordinary/legacy layouts and a header mutation
caught by whole-file hashes. This does not execute KOS movie reload I/O or the
full generation/reader lifecycle; source audit and root target gates remain.
Mode0 reader preprocessing equals pre-repair7daa exactly (SHA256
`4a2e8885d91d8f1348db56c711b5d98d01f9114cccf926972774ef59e694355b`).
No extra SDK work ran. Full linked OFF identity, actual memory/movie/render and
console acceptance are pending independent root qualification.

The historical private `camera-transform-counts.json` is not a current release
performance estimate: its script calls `est.selection` without lod_px, inheriting
5.0, while the release uses20. Those selected/savings counts must not be reused
as current. All exact strip-sharing/reader evidence above covers every retained
meshlet/LOD and does not depend on that camera model or claim timing gains.

Frozen source control11109 completed: see strip-share-host-11109.json,
strip-binding-controls-11109-host.json and
composition-controls-stripshare-11109-host.json. Exact96 composition comparisons
across8 configurations plus the stale-reset mutation pass, including the
SELECT_ONLY1/REPLAY_LEAN1/SUBMIT_BATCH1 combination. These source controls remain
pinned to11109; later origin82d/current recipe target qualification is separate.

Reproduce binding/layout (same pinned compact bytes also exist in the RAM map):

```text
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 python3 port/dreamcast/tools/d367/dedup_offline23/check_strip_binding.py --source-tree /root/work/lanes/dedup-offline23 --expected-source 11109d046d42c352c801c6c1a8e5a701de9bfe52 --baseline-native /root/re4payload/t164-20261018/tree/dc/native --legacy /mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023 --compact /dev/shm/dedup-stripshare-host --output /dev/shm/CHOOSE-FRESH-OUTPUT
```

For an immutable or detached11109 source tree, pass its actual path above.
The checker requires exact HEAD and tracked-clean source. RAM map r100/r101/r103
files hash exactly to the private r100-stripshare-v1/r101-stripshare-v1/
r103-stripshare-v1 variants. No existing variant may be overwritten.
