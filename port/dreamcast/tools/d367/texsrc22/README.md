# Portable texsrc22 source tools

This unit ports the PR53 classifier/converter source from
`0a905de5babb2c6be30dbac40c71df666773f390` (merged into the historical
`wip/texsrc22` at `bfce2800cbd726b18fbb416ee39d64c07ab00c23`) onto integration
`9f6a25c61df6ad635c46e837b2371fc8b523ada6`. It uses the current checked-in
pack readers, three mip encoders and `mipmap21/mip_quality.py` unchanged.
No old telemetry, private classification ledger, scene table or approved-key
list is imported. The original branches and evidence are preserved.

## Classifier

`classify.py --help` describes the explicit input files/directories. It keeps
all supplied origins, package names, validated R4PW material references,
resident references, historical positive drawing evidence and unresolved
text/raw hints. R4PW placement bytes are never promoted to material bindings.
Missing resident evidence, malformed packs/worlds and ambiguous scoped aliases
refuse. HUD aliases retain priority regardless of source ordering. Shared
Ganado origins without a resolved consumer stay held; all41 shared originals
remain retained. Static format eligibility is not runtime use, original PS2
ancestry, minification, room/memory fit or conversion permission.

Both reports require new, distinct paths. The JSON records SHA256 identities
for all supplied input files and every native/resident file actually scanned,
plus the classifier source. These are read-byte identities, not an assertion
that caller-provided evidence is complete or authoritative. No output permits
pruning. Existing inputs and outputs are never overwritten.

## Candidate converter

`convert.py --help` describes the CLI. Default OFF verifies the source archive
and returns its entire bytes, including archive padding, unchanged. It needs
no selection or quality gate. The CLI writes only explicitly requested new
output/report files; it refuses in-place or existing output paths.

ON requires `--enable`, an explicit nonempty selection, the exact pinned
quality-gate source and an explicit room hold manifest. The selection schema
`re4dc-texsrc22-selection-1` binds source pack, gate source and hold bytes by
SHA256, with unique lowercase approved keys. A classification TSV is never an
approval manifest. Missing keys, malformed/unsupported packages and partial
cohorts refuse before output. Only square single-image VQ, twiddled16-bit and
PAL4 encoders are used; no recovery re-encoder is introduced.

The selected gate executes its SHA-checked source bytes directly, ignoring
cached bytecode. The gate must inspect every final encoded level through1x1.
Colour/coverage failures, room holds, existing mip chains and unselected
packages retain their exact originals; all-held output retains the complete
original archive. Passing candidates preserve decoded base pixels, base
payload, material identity and canonical package CRC. The report binds input,
output, selected package identities, selection/hold/gate and converter source,
plus resolved current repository helper source hashes. It is a private
candidate report, not permission to publish or adopt the resulting assets.

Run in a fresh Python process with `-I -S -B` and a fresh absent
`-X pycache_prefix=/absolute/owned/fresh-prefix` (also set
`PYTHONPYCACHEPREFIX`/`PYTHONDONTWRITEBYTECODE` for subprocess tests). This
keeps current repository helper imports out of pre-existing cache namespaces.
Only Python standard-library facilities are needed with `--engine python`.
No installed package, asset conversion or emulator is needed for host tests.

## Host verification

From this directory, `python3 -B -m unittest -v test_classify test_convert`
runs35 synthetic-data methods against the current integration gate, with no
skips. For a sealed source run, use the fresh process/cache settings above and
256MiB address-space/120-second limits. The tests exercise all three actual
encoders and the final1x1 level, OFF whole-archive identity, held/unselected/base
identity, source/hold/gate/selection mismatches, malformed packs/indices/worlds,
missing resident/key inputs, HUD and late shared origins, historical positive
references, output no-clobber, incomplete gate levels, and a real poisoned
unchecked-hash gate cache. No private pack or image is opened.

Only these source tools/tests/docs are added. Runtime, build recipes, assets,
scene decisions and normal programme bytes have no changed source input.
There is no target build, generated game data, new visual acceptance, memory,
frame-time or physical-console claim. Later candidate use remains subject to
its current source/consumer, quality, memory, room, disc and visual gates.
