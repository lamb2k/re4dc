# EF09 prepared world facts

WORLD_PREPARED09 is default0. Enabled use requires the existing part plan,
`MOVIE_WORLD_ARENA=1` and `STATIC_OBJ_LIFETIME05=1` so allocator identity comes from
the existing Room4 producer. No new resource manager, renderer or asset format.
Absent/zero preserves the preceding source branches, plan layout and guards.

The first consumed slice uses the loader-validated sorted witness table as an
index. Exact EF08 tickets carry the resolved index through queued flush, which
no longer repeats the membership scan. Exhaustive N=0..256 tuple cases measure
10 worst-case comparisons including final match, not a universal bound of8.
All existing receipt source/part/placement/view/material/completion checks stay.

The second slice advances a local plan incarnation before close/free and
across existing open/movie-unpublish/reload. Room4 generation, exact cell bytes
and allocator incarnation are retained outside plan payload and checked before
record/bounds dereference or free. The package cell token, room and existing
source package revision are checked too. Pointer equality is only a supporting
comparison. Same-generation/address/size replacement cannot authorize an old
plan or stale close. A capacity flush rechecks the local plan lease before
further record/key access. The existing movie reader protects synchronous work;
queued matrices, material keys, UV and sky snapshots remain copied as before.

An allocator callback must leave the expected local/source/room publication
unchanged before the first candidate write. A newer nested publication is not
overwritten. Zero/unknown identity or lost attribution refuses reuse and never
frees an unproven pointer. Any potentially retained optional return is counted
in unproven_return_bytes; retries are latched for that room generation. It is
reclaimed by its actual owner/heap retirement, not by guessing at a recycled
address. This bounded exceptional retention is not a memory-saving result;
live memory acceptance remains required. Token exhaustion uses ordinary drawing.

Ordered records retain encounter order, key and meshlet facts. The consumer
references current Ps2Part metadata directly rather than reconstructing a
16-byte temporary from the record. Live foliage/transparency policy, UV, source
root pose, texture binding and current camera remain in their original paths.

Optional24-byte placement boxes use only budget remaining after base records
within64KiB and the96KiB heap floor. Tail allocation/overhead failure retries
the smaller base request; it never sacrifices an admitted base plan or evicts
other backing. Boxes use the existing world_box arithmetic, expanding half
extents by one representable step; nonfinite/oversized/inverted uncertainty
provides no early capability. Before view setup, current portal receipts may
reject only a whole hidden immutable placement with a valid plan lease, intact
static mapping and no dynamic slot. Moving/root-pose/resting-dynamic, unknown
mapping, claimed groups and unproved geometry retain the original view path.
No queue transform sharing is introduced.

## Checks

```bash
python3 port/dreamcast/tools/cloud/build31/world_prepared09_host.py --output "$OUT/host"
python3 port/dreamcast/tools/cloud/build31/world_prepared09_host.py --sanitize --output "$OUT/sanitized"
python3 port/dreamcast/tools/cloud/build31/portal_completion_host.py --prepared09 --output "$OUT/completion"
python3 port/dreamcast/tools/cloud/build31/portal_completion_host.py --prepared09 --sanitize --output "$OUT/completion-sanitized"
```

Use fresh output directories. Actual production plan lifecycle, direct metadata
consumer, early-consumer block and literal original world_box are compiled with
controlled allocator/source/portal edges. Current suite:7,106 main checks,
86,420 indexed lookups and450 ordered live-policy cases, plus Make guards.
It covers same-generation same-address cell replacement, stale close, heap reset,
source/package change, callback reentry before write, token0/exhaustion, optional
allocation/headroom/cap refusal, dynamic/root-pose/uncertain fallback and early
cut before view setup. Existing628 portal-completion checks retain actual
runtime/chunk_emit/flush boundaries, source/view changes and partial outcomes.
ASan+UBSan run; leak inspection is disabled. This is not full renderer execution,
actual authored-wall proof, gameplay/STRICT, physical memory/headroom or timing.

Target profiles are in world_prepared09_profiles.json. Plan-only and compatible
portal/batching are explicit separate validation compositions. Current source
cells and geometry-authored CFG/PKG/portal-proof.json are still needed for real
occlusion/magenta/look acceptance, together with reset/reentry/movie, STRICT,
full memory and net console cost. No broad ALLON or default promotion is made.
