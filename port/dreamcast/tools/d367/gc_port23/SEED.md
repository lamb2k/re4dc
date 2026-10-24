# Historical texture seed helper (I-001)

`build_reviewed_seed.py` is an offline, private evidence generator. It binds a
pinned historical `texpak-provenance.tsv` to the exact original `dc/tex.pak`
selected by the audit's package JSON and full SHA256/size manifest. It never
reads new guest failures, scans a private store, changes assets, updates a
baseline, or adds a room because an asset is resident. This is source/evidence
for a later bounded runtime lookup; do not compile or retain the whole catalog
in the game. No runtime, recipe, rr, staging or release integration is included.

The historical audit records **loads**, not accepted draw/play emissions. Every
output evidence string says `historical_load_only`; the report leaves emitted
rooms empty. These receipts establish neither coverage nor a GC-ASSET pass.

## Inputs and outputs

Run with Python 3.9 or newer. Pass `--audit`, `--manifest`, `--package` and each
corresponding `--*-sha256` from the reviewed old evidence. Explicitly provide
each permitted readonly `--store-root`, and a new `--out-dir` outside those
stores. Source paths in the old package receipt must resolve inside an allowed
store. No asset files are copied. A symlink escape, changed pin, replacement,
mutation, duplicate identity, wildcard room, wrong pack/member size, overlapping
index, unsupported header or audit/pack key-set difference fails generation.
The pack is hashed before and after reading members and its file identity is
checked against its path. Outputs are deterministic for identical pinned input
bytes, source path and audit path label; existing output directories are refused.

The generator writes three JSON files, all with `schema: 1`:

- `catalog.json`: `entries` with exactly `kind`, `id`, `sha256`, `provenance`,
  `evidence`, `source`. Kind is `texture`; id is lowercase `crc8-fnv8`; SHA256
  covers the entire immutable RE4TEX member, including its exact `RE4DCTX` header.
  Source identifies the verified pack, byte offset and full member size.
- `reviewed-seed.json`: exact exception `entries` with only `room`, `kind`, `id`,
  `sha256`, `provenance`, `reason`, `owner`, `evidence`, matching `judge.py`.
  Rooms are four lowercase hexadecimal digits (`r111` becomes `0111`). Only
  audited loads receive room entries. Provenance is `gc` or `unknown`; reason
  and owner are explicit. This file is a proposed initial review seed, never an
  automatically accepted or forever baseline. Existing only-shrinking policy
  still applies when the integrator compares with the last accepted list.
- `seed-report.json`: input/pack pins, counts, historical class/load/residency
  distinctions, unproven old PS2 count and omissions. Catalog scope includes old
  loads, residents and native references; resident/reference presence alone
  never expands exceptions to other rooms.

The old classifier used path and filename heuristics for PS2/native/store
classification. Those claims do not prove origin. All unproven content remains
`unknown`, including GC-key/PS2-class entries and locally generated VQ/mip/store
conversions. A GC key can hold PS2 bytes, but the key itself proves nothing.
The old audit hashed pack members: its four loose texture overrides are listed
as unbound omissions. A different loose payload digest gets no exception.

## Optional independently reviewed origin proofs

Supply `--proofs` together with `--proofs-sha256`. The proof document is
`{"schema":1,"entries":[...]}`. Every row has exactly `kind`, `id`, `sha256`,
`provenance`, `evidence`, `source`. Strings must be nonempty; kind is `texture`;
id and full payload digest must exactly match an already selected historical
member. Provenance is `ps2`, `authored` (documented original Dreamcast artwork),
or `gc`. `source` and `evidence` cite the independently reviewed origin receipt.
The helper verifies the binding and strict structure, not the truth of a human
source-origin review. Do not feed the old heuristic labels back as proofs.

PS2/authored proofs remove only matching exceptions; GC proofs keep exact GC
exceptions. Proofs cannot introduce identities, new rooms, wildcard scope or a
different payload under an old identity. Duplicate or stale proofs fail.

## Qualification and limits

`PYTHONDONTWRITEBYTECODE=1 python3 test_seed.py` runs small synthetic fixtures
in RAM on Linux. Set `GC_SEED_REAL_EVIDENCE` to the old audit evidence directory
to also verify its three pinned receipts, full original pack and exact real
sample `001c0ae3-f6006faa`. No game bytes are checked in. Tests include header
hashing, determinism, resident-only behavior, stale proofs/pins, duplicate keys,
wildcard/new-room rejection, source mutation/replacement and store escapes.

The 2026-10-23 private acceptance run bound 7,299 old pack identities to pack
SHA256 `5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da`.
It produced 2,324 catalog rows and 5,763 exact unknown exceptions for loads in
26 historical rooms. The 2,108 old claimed-PS2 catalog rows remain unproven.
No independent origin proof was supplied. This deliberately conservative seed
does not certify that every listed texture is GC or that any texture was drawn.

Source models/props, weapons, font/UI sheets, sample banks, streams, movies,
non-texture effects and unobserved rooms/scenes remain unresolved. They receive
no invented allowances. KOS, image identity, s30, TEXCHK, VRAM, GDEMU, emitted
consumer coverage and hardware acceptance were not run by this offline helper.
