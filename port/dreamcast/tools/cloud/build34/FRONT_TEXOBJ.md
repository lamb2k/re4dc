# FRONT_TEXOBJ descriptor validation — Build34

This fixes an existing default-off cache; it does not enable it in the release
recipe. The prior key bound the primary/added TPL pointers, descriptor count,
wrap mode and first texture data pointer. It could return stale GX words when
another descriptor, dimensions, format, wraps or the min/max-LOD relation
changed while that key stayed equal. Actual-source synthetic controls reproduce
seven such stale-word failures on integration
`36643bf8ab5a78c581274f28eca702ae8aa48330`. They establish a cache-contract gap,
not an observed private gameplay failure.

`src/game/trans.cpp` now validates each current descriptor's four packed GX
words on a key hit. Forced wrap models still write both source header wraps to 1,
even when the packed object remains equal. Thus two different primary TPLs that
share an added TPL are revalidated after either model mutates that header.
Changed records refresh in their existing allocation only after flushing any
preceding symbolic GX state. Key capacity, record capacity, room reset,
sequential texture swaps, out-of-set source fallback and the smaller-set tail
retain their prior behavior. No new cache storage or public ABI is introduced.

The source already maps its original diagnostic filename/line numbers. A
`#line 2302 "D:/Bio4/Prog/trans.cpp"` boundary after the optional cache restores
the original following function location. Both legacy HALT sites therefore
remain 2044 and 2465. The target gate compares raw preprocessed files and objects;
it does not normalize the diagnostic change away.

## Actual-source host checks

Run from the repository root with a C++20 host compiler:

```sh
python3 port/dreamcast/tools/cloud/build34/front_host.py \
  --output /tmp/re4dc-build34-front-host
python3 port/dreamcast/tools/cloud/build34/front_host.py --sanitize \
  --output /tmp/re4dc-build34-front-sanitize
```

Choose unused output directories. The runner extracts the actual cache block,
actual uncached native initialization loop, actual GX initializer, TPL getter
and texture-swap body. It uses the real TPL layout and asserts accessed SH-4
offsets in the target fixture; host pointers are naturally wider. Its oracle
compares every effective/materialized GX word and source header side effect.

Both normal and ASan/UBSan runs pass 23 scenarios and 173,714 checks. All seven
old-source mutation controls fail in the expected way. Coverage includes
secondary data, width/height, format, wrap and mip changes, descriptor-pointer
reuse, same-address recycling, forced-wrap hit side effects, shared added-TPL
aliases, added-only sets, sequential swaps, out-of-set fallback, count changes,
tail preservation, room/stage changes, both capacity resets and repeated
snapshot flushes. LeakSanitizer is disabled because this sandbox cannot traverse
the required process map; address/undefined checks remain fatal.

These are cache/helper tests. They do not execute the complete native model
walker, transform geometry, run a private route or qualify image/STRICT
equivalence. The release's `ACTOR_TRANSACTION` setting rejects
`FRONT_NATIVE=2`; the helper snapshot test is not a complete replay2 gate.

## Bounded SH-4 cost

The existing pinned compiler/model can reproduce the cost fixture:

```sh
python3 port/dreamcast/tools/cloud/build34/front_cost.py \
  --output /tmp/re4dc-build34-front-cost \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT"
```

Set those variables to the installed SH-4 compiler, pinned KOS tree and SH4ZAM
tree used by the regular Build34 target gate. The runner derives current public
recipe trans flags from Make. The actual TPL/GX/swap providers compile in a
separate translation unit so their external calls cannot disappear through
fixture-only inlining. This uses the existing bounded model/link fixture; no
production assembly or linker configuration changes.

All 34 baseline/repaired cases pass, including deliberately incorrect old dirty
hits. Warm/cold-I cycles below assume a perfect D-cache. Loads/stores are
executed instructions; lines are unique 32-byte address footprints, not misses.

| Repaired helper case | Warm / cold-I cycles | Loads / stores | Data lines | Peak stack |
| --- | ---: | ---: | ---: | ---: |
| Stable hit,1 descriptor |233 /479|81 /15|25|300 B|
| Stable hit,8 descriptors |667 /913|207 /15|39|300 B|
| Stable hit,32 descriptors |2,155 /2,401|639 /15|84|300 B|
| Stable hit,248 descriptors |15,547 /15,793|4,527 /15|487|300 B|
| Forced-wrap hit,32 descriptors |2,123 /2,369|607 /79|84|300 B|
| Dirty last descriptor,32 records |5,442 /5,797|1,264 /408|119|328 B|

The old unchecked hit was 159/374 cycles independent of descriptor count. The
uncached production initializer costs 144, 690, 2,562 and 19,410 warm cycles for
1, 8, 32 and 248 descriptors. Validation therefore loses to uncached initialization
at one descriptor and leaves only a small advantage at eight in this fixture.
The prior historical cache benefit must be measured again.

For a deliberately assumed 200 repeated 32-descriptor lookups at 200 MHz, the
repaired helper costs 2.155 ms versus 2.562 ms for the uncached initializer; the
unchecked old helper was 0.159 ms. These are sensitivity numbers, not observed
frame timings or a prediction of FPS. The cost excludes transforms, material
binding, swaps, periodic logging, D-cache misses and all other rendering work.
Cold-I cases are isolated, not additive. Dirty baseline results are known wrong
and are not usable alternatives.

The bounded fixture's executable bytes grow 2,400->2,640, with unchanged zero-fill
storage. This is not a whole-production-TU size result; the Build34 target gate
provides that separately. The retained key/record arrays are 512/8,192 bytes, with
no new fields. Stack peak for stable hits changes 304->300 bytes; a repaired dirty
refresh reaches 328 bytes.

## Qualification still required

Keep `FRONT_TEXOBJ=0` until a matched current-recipe 0/1 test passes STRICT,
image/look and net frame-cost gates. Exercise same-room texture archive reuse,
weapon/menu/movie transitions, and wrap/shared added-TPL content. Use
`FRONT_NATIVE=1` in the current profile. Any replay2 investigation needs an
explicit matched `ACTOR_TRANSACTION=0` profile and its full Make compatibility
gate; do not silently turn off release features in the primary comparison.

Committed compact receipts are [host](receipts/front-host.json),
[sanitized](receipts/front-sanitized.json) and [cost](receipts/front-cost.json).
They bind source hashes, extracted fragments, Make flags and model metadata.
No game data or console result is included.
