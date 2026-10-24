# One-frame selected world emission census

Source-only diagnostic for the world-emit23 four-arm comparison. Base:
`a5e972e44096410253ad93164b84d92e3c22655a`.

`SCENERY_EMIT_CENSUS=0` is the default and adds no compiler flag. Set a decimal
minimum UI frame, for example `SCENERY_EMIT_CENSUS=360`, on a dedicated diagnostic
twin with the exact target warp. The first pass0 at/after that threshold captures
one UI frame in one room, across passes0/1/2. Check BEGIN's room/frame. There is
no automatic second attempt after an incomplete capture; use a new run.

This counts the actual selected chunk queue, not an offline camera estimate or
the whole loaded package. One part can occur multiple times for distinct
placements; rows retain its placement-array slot, package part index and
texture/source key CRC/FNV. Flush IDs span the captured frame. Zero-pick parts
remain visible.

- `plain/indexed`: selected meshlets classified by strip_count bit15.
- `pv/iv`: sums of the complete vertex_count of those selected meshlets.
- `zero`: selected picks with nr0; `iz` is the indexed subset, `zv` its
  full vertex sum. Whole sentinel0xff is not nr0.
- `whole/partial/span`: selected whole and nonempty partial picks and their
  contiguous transform-input span (full, hi-lo+1, or zero).
- `tried`: entry into the actual emit_pick before binding/borrowing, including
  an entry that fails before any geometry. It does not imply submission.
- Part result1: chunk_emit completed;0: fallback;-1: abort;2: not attempted.
  A completed part can select zero picks. There is no accepted-corner counter.

The span is before any dedup optimization. The planned current-recipe comparison
has SCENERY_DEDUP0; do not call it actual transformed count under another dedup
mode. Full indexed gather and selected span must remain separate. In particular
EMIT_PREFETCH omits the unused gather for nr0 but still binds/borrows/primes.

The diagnostic does not affect selection, gather, transform, strip order,
source state or renderer returns. It increments attempt metadata and reads
the retained immutable queue at flush exit. The census object is declared before
SubmitScope, so its destructor logs only after batch/SQ close, also on abort.
A bounded48-element progress array retains exact per-part attempts even when
fallback continues to a later part. No heap or package writes are introduced.

All metadata is gated away when off. Expected SH4 layout from member widths:
State28B BSS, Pass16B stack, Flush approximately424B stack including its384B
progress array, plus4B per existing queued ChunkPart (192B at48). These are
layout estimates, not target compiler/link/peak-stack or heap acceptance.
Logging/hash overhead makes this unsuitable for timing measurements. Actual
target syntax, linked memory, raw-off identity and guest capture remain pending.

## Host controls

```sh
PYTHONDONTWRITEBYTECODE=1 python3 port/dreamcast/tools/d367/world_emit23/test_census.py \
  --output /dev/shm/world-emit23-census-host.json
```

All compilers/binaries/temp files stay in /dev/shm; core dumps are disabled.
The runner extracts the actual ChunkPart declarations, complete chunk_flush
body and production emit_pick entry hook, then compiles them with the actual
diagnostic helper. The geometry method is a controlled adapter; this is not
a complete emitter/FTRV/clipper or selector-equivalence test.

Eight replay/batch/prefetch configurations cover mixed plain/indexed, whole/
partial/nr0, zero-pick parts, multiple drains,48parts/320picks, fallback
continuation and abort after earlier success. Reversing destructor order is
a meaningful negative: logging while SQ is held must abort. Maximum-width
count rows fit the existing256-byte logger. The real generated log passes the
parser; incomplete frame, forged totals, failed part, duplicate row and wrong
room controls fail.

Includes-stripped complete native_static preprocessing is identical to the
base with the knob absent and explicitly0 under the current selector/replay/
batch profile. The isolated make target prints the same flag command absent/
zero, accepts360, and rejects malformed values/dependencies. This is a source
guard/command control, not a full SDK object or programme identity.

## Read a capture

```sh
python3 port/dreamcast/tools/d367/world_emit23/census.py /explicit/run-output.txt \
  --room 0x101 --output /explicit/world-census-r101.json
```

The parser requires all three passes, complete selected replay, consistent
per-part/flush sums and no bad ranges/overflow, duplicate/missing/orphan records
or wrong room. It refuses an aborted/fallback frame instead of silently
presenting a complete census. Raw log rows still preserve its selected and
attempted prefix for diagnosis. This parser does not prove pixels, speed,
physical PS2 provenance, runtime quality choice or safety gates.

Use the external world-emit23/PREFLIGHT.md for four arms, current source/
programme/data pins, separate timing/still runs, gates and console pair. No
production recipe enablement is included here.

## Ordered capture protocol repair

Independent review of2adba1332 found that the original parser checked a bag of
rows without enforcing source event order. Reversed rows, a completed flush
moved after FRAME_END, a flush relabeled into the wrong active pass, and a
threshold above the captured frame could pass. This tools-only successor
consumes BEGIN, passes0/1/2, scoped flush/part/count closures and terminal
FRAME_END in order. Flush IDs are globally contiguous from1 across passes.
Threshold must be1..10000000 and not exceed the captured UI frame. Missing,
unknown, duplicate and unsigned-out-of-range fields are refused.

The actual generated host log supplies twelve protocol mutations, all rejected,
and a valid cross-pass flush positive. Earlier aggregate/safety controls remain.
Runtime/header/make files are unchanged by this repair. Source integration
review is bounded to the actual SUBMIT_BATCH1/PVS0 profile; the selected-affine
proposal is unapplied and unadmitted. No compatibility or qualification of that
future patch follows from this census milestone. No SDK/guest gate has run.
