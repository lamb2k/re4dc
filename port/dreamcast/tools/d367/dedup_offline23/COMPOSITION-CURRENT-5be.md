# Composition at merged integration 5be

PASS_HOST_COMPOSITION_ONLY against exact
`5be38f009f9ae4d42daff69dacc537e8230bcfca`:96 comparisons across8 configurations,
plus the deliberately missing-cache-reset mutation was detected. All8 output
digests also match the preceding frozen footprint3467 host control.

The snapshot contains211 files (2,462,226 bytes), each read from that exact Git
commit object into `/dev/shm/dedup-composition-source-5be38f009`; files are marked
read-only. The source-pins manifest hashes every retained file and is verified
by the existing runner. The runner source/fixture hashes and source/extracted
method hashes are in `composition-controls-5be-host.json`.

`RE4DC_SCENERY_SELECT_LEAN2=0` is now explicit in each host compiler invocation
and in the receipt. This is the default-off control requested for the merged
source. No LEAN2 ON behavior is asserted. The fixture supplies preselected picks;
it does not execute chunk_select, so this receipt is not selector acceptance.
SCENERY_UV_SNAPSHOT remains at the existing off boundary; no UV-snapshot ON
composition is asserted.

The existing cases compare encoded/decoded positions, fresh/reused contexts,
and submit-batch0/1. They cover inside/near/far/screen shapes, successful flow,
scratch shortage, owner/bind failure after earlier success, encoded-to-empty,
plain/indexed/new encoded transitions, SG span and UV/color seams, cache/state
words and balanced locks. Actual extracted emitter, corner/borrow/context getters,
emit/restart/replay and portable clipping bodies are used. Only the two existing
SH4 FMAC instructions are adapted to host arithmetic on exact dyadic fixtures.

Command (owned runner):

```text
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 python3 port/dreamcast/tools/d367/dedup_offline23/check_composition.py --source-tree /dev/shm/dedup-composition-source-5be38f009 --expected-source 5be38f009f9ae4d42daff69dacc537e8230bcfca --output /dev/shm/dedup-composition-5be38f009-host
```

All compiler scratch, binaries and detailed traces stayed in RAM. The live
integration/build trees were not edited or leased, and no SDK/full-programme
build, staging, guest or media action was run. SH4 optimized clipping/FTRV/FSRRA,
real-room output, performance and the fresh linked memory gate remain separate.
