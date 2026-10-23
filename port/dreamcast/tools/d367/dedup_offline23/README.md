# SDO3 offline scenery dedup prototype

This is source/host evidence only. No target build, staged disc, Flycast run,
console result, or production recipe change is established here.

The converter preserves every emitted strip's ordered six-word corners after
reference decoding, including UV and colour seams. It preserves the R4IM and
R4SG file lengths. Its output uses alternate ps2-dd3.* names and must never be
read by a runtime that does not understand the marker.

## Format

R4IM v3 prelit only. Header reserved[2] (offset72) is the original body CRC;
reserved[3] (offset76) is little endian 'SDO3' (0x334f4453). Current input values
are zero, and the existing reader ignores both words. All other table offsets,
counts, bounds, palettes, classes, LOD records and material records are retained.
The body CRC is recomputed after encoding.

For a plain meshlet, strip_count bits0..6 are the actual strip count and bits7..14
are the repeat count. Bit15 still marks indexed meshlets, whose original full
15-bit strip count is preserved. Plain strip counts over127 are left unchanged
and therefore cannot occur in an SDO3 package unless already <=127: the current
three real room packages have maxima25/28/25. The runtime must reject oversized
plain counts at conversion/admission rather than silently truncate them.

Unique-position corners come first in their original order; repeats follow in
their original order. Each repeat stores (first_corner, 0x5344, 0x4f33) in XYZ,
retaining its own UV/colour. first_corner must address a non-repeat; chains and
out-of-range references fail admission. Every encoded vertex belongs exclusively
to this meshlet. Indexed and aliased plain meshlets retain their original bytes.

Strip indices follow the permutation. Existing R4SG group bounds/end offsets
remain unchanged; group corner ranges become the unique-source range needed by
that group's strips. Thus an arbitrary surviving group subset primes all firsts
its repeats use. The draw may populate other unused repeat slots from unprimed
firsts, but those slots cannot be submitted by that subset. R4SG binds the new
actual R4IM body CRC/size and retains its original policy sidecar CRC.

## Required consumer changes

SCENERY_DEDUP=3, default0, must select the alternate mesh and alternate R4SG.
The standard filenames and knob0 reader remain unchanged. A marker not explicitly
recognized for the mode must fail closed. A missing alternate may use the base.
The reader must validate sources/tags/counts, aliases and strip ranges using no
heap allocation. No lets/src/masks section or room-file dependency is needed.

Every CPU coordinate reader must resolve references: the fast vertex path
transforms unique corners only, the repeat filler reads strided source bytes,
and generic strip/near/far clip paths decode XYZ while retaining own UV/colour.
Classify-none/screen paths must not transform encoded XYZ. World movie reload
must reread the alternate and must not reorder it. Standard world lighting and
impostor paths use other packages; SDO3 admission is restricted to prelit PS2
world packages. The original header CRC is a semantic identity for existing
scoped sidecar provenance only, never a claim that the actual bytes are unchanged.

Package bytes do not grow. Runtime state can reuse dedup pointers and the existing
meshlet/gather/cache records; any added stack/context words and image growth must
be measured separately. The s30 floor, KOS squeeze and knob0 identity are still
unrun gates. Current recipe room files can already contain stale SCDD sections;
mode3 must not depend on, enlarge, or retain those sections specially.

## Host results at source451bed6f

Inputs: t164-20261018 payload R4IM; r101 R4SG also from payload. Current recipe
sidecars resolve to mip22b-20261022; they are retained, not regenerated here.
These counts cover every loaded meshlet including fallback/LOD, not a camera
sample or a frame-time result.

| Room | Corners | Encoded repeats | Encoded meshlets | Indexed fallback | Aliased fallback | R4IM bytes |
|---|---:|---:|---:|---:|---:|---:|
| r100 |108869|14564|1131|43|83|1537920|
| r101 |93576|11934|839|227|452|1283520|
| r103 |79169|13009|767|146|337|1074688|

r101 R4SG remains117152 bytes. r100/r103 currently have no R4SG. Five synthetic
host tests pass, covering ordered seams, isolated-group priming, unknown/default
mode rejection, stale identity/CRC, malformed sources/tags/counts and chains.
All three real packages pass the complete ordered-corner semantic comparison;
r101 also passes every strip group's unique-source coverage check.

Evidence: C:/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/.
Private inputs and encoded outputs are never committed.