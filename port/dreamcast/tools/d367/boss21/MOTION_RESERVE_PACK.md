# Pack v2 cold motions within existing reserved backing

This is the capacity component following [the pressure accounting repair](MOTION_PRESSURE_REPAIR.md), commit `c5fbf44d`. It is a separate default-off candidate. No room recipe, asset, hot-set producer, gameplay, or strict v3 policy changes.

## Confirmed failure and bounded repair

QA12 reached the original after-s20 r100 ambush using normal input on the fixed QA program. Three recurring cold FCVs (entries24/26/91, 11744/7744/12224 bytes) repeatedly replace each other in two 32416-byte cells despite their combined31712 bytes fitting one cell. The retained trace ends at703 loads/682 evictions. Its actual room heap had93824 bytes free, so the existing262144 cold-pool and524288 spill margins correctly blocked heap fallback. The accounting component alone cannot resolve that slot-capacity failure.

Castle J independently retained em11 windows using entries0/6/86 (48960 bytes) or0/6/152 (63968 bytes), with0+6 fitting one32416-byte slab. Its larger four-key temporal union is not proof of simultaneous use. Sampled zero/one pins in these traces are lower bounds, not source concurrency limits.

`MOTION_RESERVE_PACK=1` lets ordinary v2 cold clips share aligned first-fit gaps within each existing slab. It derives occupied intervals from the existing slot table. It never relocates a cached FCV, changes its bytes, or allocates new backing/metadata. A cache hit takes the existing path. A cold miss first looks for a fitting gap. If none exists, existing spill/pool policy remains; if those margins refuse, the existing cold LRU discards unpinned reserved occupants until a gap fits. No compaction or movement occurs, including for unpinned neighbors.

Enable an isolated integration candidate with:

```
MOTION_RESERVE=1 MOTION_PRESSURE_BYTES=262144 MOTION_PRESSURE_BACKING=1 MOTION_RESERVE_PACK=1
```

`MOTION_RESERVE_PACK` accepts0/1, defaults0 and requires the accounting component. No recipe enables it here. Heap-key cap, fixed two-slab allocations, per-archive size bounds, heap margins, current/previous/shape motion selection, and lease ownership remain unchanged. Strict v3 profiles still admit only one clip per slab, reject both pinned and never spill or join the heap pool. This does not qualify a source working set larger than available backing or repair v3 two-cell churn.

## Ownership and failure handling

All packed addresses remain32-byte aligned and stable until their own slot is evicted. Pins prevent eviction. Subregions are recognized by owning slab range in discard, pressure, OOM and movie eviction. They are never individually freed. Retirement clears slots and frees each original slab once. Read retries, CRC/FNV, proxy/header and key-offset validation stay intact; failure traps keep borrowed backing rather than freeing an interior pointer.

The existing motion bridge checks allocation ownership by reading a header immediately before its argument. Menu-return recount therefore resolves a packed FCV to its original slab base before calling that check. This is ownership adaptation for interior pointers, not new menu/movie hot restoration. Suspended slot tables remain behind the existing hold guard; no new mutable state, layout or public statistics fields are added.

## Actual-source tests and target build

Run `python3 port/dreamcast/tools/d367/boss21/test_motion_pressure.py`. The asset-free harness includes the actual loader, generates synthetic valid FCVs and mocks only KOS/transport/allocation. ASan/UBSan/leak checks pass for baseline, accounting-only and packed variants, including normal and lean leases.

Each of the three retained size sets above is cycled60 times. The accounting-only control has60 loads/58 evictions; packing has3 initial loads/0 evictions/57 hits and zero new allocations. Tests also cover four coactive leases (pointers and relocated bytes unchanged), failure with all fitting regions pinned, unpin then safe replacement, an interior hole, movie/pressure/OOM exclusions, held/resumed ownership checks, retirement, and read/identity/offset faults. The earlier accounting, global heap cap and strict v3 tests remain passing. These source tests reproduce capacity behavior; they are not runtime performance claims.

SH4 native_motion.o builds pass after merging fresh upstream `bfc8aab6` into the isolated branch. PACK0 stripped object exactly matches accounting-only SHA256 `7d47e4b801d234f6cc9bd0016fd790fe7d62d45f4ae9c35a62907267e9aa0b1f`. Packing adds496 text bytes (8712->9208), zero data/BSS (BSS557 unchanged). See [the receipt](motion-reserve-pack-receipt.json).

Full linked-program identity, QA's current after-s20 gameplay/I/O, castle continuation, menu/movie return, KOS reserve and console remain integration gates. The five-key QA temporal union totals69792 bytes, exceeding64832 reserved bytes; its simultaneous residency requirement is unresolved. Packing eliminates the demonstrated three-cell mismatch but does not establish whole-fight no-I/O closure. Fragmentation can also prevent a fit despite sufficient aggregate free bytes; stable pointers deliberately rule out compaction. There is no speed, console acceptance or release claim from the host/object checks.
