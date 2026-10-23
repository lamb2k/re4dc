# Bounded indexed provenance contract (source design, not runtime integration)

Frozen baseline: selected target objects at 304eef6b9 add 54,444 B before link.
Actual linked image, heap and complete I-001 gates remain open. The prototype
in catalog_index.py does not replace the current runtime borrowed catalog yet.

The disc catalog is an immutable, read-only CD input. Install streams its whole
SHA256 with 512-byte scratch and compares the independently reviewed release
pin. No mutable/replacement-catalog path is established; no Merkle protocol or
resident record array is needed. The build formatter does not determine origin:
its input must already have exact full-payload provenance review. A filename,
container key, local conversion or evidence string alone supplies no verdict.

The 128-byte little-endian header contains magic GCIDX001, schema 1, record
count, fixed record size 112, records offset 128 and zero reserved bytes. Each
record holds kind[16], id[48], actual immutable payload SHA256[32], provenance
byte (unknown/GC/PS2/original-authored) and zero padding[15]. Strings are
nonempty ASCII tokens with explicit NUL and zero fill. Records sort by exact
kind/id/full SHA; duplicates with contradictory provenance are rejected. File
length must equal header plus count times record size. The builder and pinned
file are deterministic. The catalog includes all consumer classes, not only
the 2324 historical texture rows.

A checked token is 32 bits: record index in bits 0..13, install epoch in bits
14..31. Epoch zero is invalid; reserve exhaustion before wrap. Catalog capacity
is 16,376 and eight additional indices address bounded unknown quarantine.
There is no wildcard, auto-learning or name/API-based PS2 fallback. A changed
payload under an existing key gets a different unknown identity. Quarantine
overflow is a terminal diagnostic failure, not permission to drop observations.

Proposed target API, all behind GC_ASSET_GATE=1:

```cpp
bool catalog_install(ReadAt, void* context, unsigned bytes, Digest expected_sha);
CheckedAsset catalog_bind(const char* kind, const char* id, Digest actual_sha);
void catalog_retire();
void accepted(CheckedAsset, Consumer); // bounded latch only, no I/O/hash/log
void flush_accepted();                // unlocked safe boundary
```

Install owns a borrowed read handle until catalog retirement. Bind is an
immutable-load/first-use operation: select the exact record only after matching
the full actual payload SHA. At safe first-use flush, resolve the checked
index/epoch, emit the same current GC-ASSET row and mark a 2 KiB maximum Seen
bitset. Further accepted acknowledgements increment counters without record
I/O. No per-draw disk read or hashing enters SQ/G2. Audio uses its existing
ticket plus a copied checked token; pump/first-use I/O runs after releasing G2.

Disc/room catalog retirement invalidates tokens before a new epoch is admitted.
Asset owner serial/generation remains independently mandatory: a valid catalog
index cannot resurrect a retired texture, BIN, static package or sound bank.
Persistent resident assets need an explicit renewed immutable-owner proof on
new catalog installation; copying an old numeric index into the new epoch is
forbidden. This owner renewal remains runtime integration work, not a behavior
implemented by the prototype. Deferred queues retain the original token/owner
serial and consumer mask, never resolve a new identity through a rebound info.

The expected savings are provisional: Entry index+mask can replace 32-byte
digests; indexed Seen replaces the 16 KiB digest-prefix array. Model and audio
records may use the same checked identity. Price the actual representation and
linked sections before choosing capacity or borrowed storage. No coverage may
be removed to fit a memory target.

Negative controls cover wrong file pin, changed kind/id/payload/provenance,
reordered records, bounds, duplicate identities, exact PS2 bytes under a GC key,
changed bytes becoming unknown, nontexture classes, stale tokens after install,
bounded unknown overflow and epoch exhaustion. Actual SQ/audio-lock, asset
retirement and room END integration tests still belong to the runtime work.

Allowlist reasons/owners and last-accepted only-shrinks remain separate judge
inputs. Generating this catalog never expands an allowance from a new guest
failure or upgrades old unproved classes.
