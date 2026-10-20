# Motion pressure backing accounting candidate

This default-off patch fixes an accounting error in the shared motion loader. It does not change motion selection, hot-set preparation, cache capacity, source evaluation, movie/menu restoration, or v3 admission.

## Problem and change

With `MOTION_RESERVE=1`, binding admission already allocates two fixed cold slabs. Their occupied payload is also counted in `stats.resident_bytes`. The pressure path used that logical total before every miss, including a miss that only fills a slab. It could therefore discard heap-backed hot clips without freeing any memory needed by the incoming load. Discarding an occupied slab also frees no allocation.

`MOTION_PRESSURE_BACKING=1` applies the existing pressure budget only immediately before an actual heap-key allocation. It derives the aggregate heap-backed payload across all four bindings and excludes data pointing at either fixed slab. The existing global LRU remains, with pins protected; only reclaimable heap keys can be pressure victims. A reserved fill or replacement does not run heap pressure. The normal cold-slab LRU still replaces an unpinned slab when its existing policy requires it.

Enable for an isolated integration candidate with:

```
MOTION_RESERVE=1 MOTION_PRESSURE_BYTES=262144 MOTION_PRESSURE_BACKING=1
```

The make guard accepts only 0/1 and requires reserve=1 plus a nonzero pressure budget. The default is 0. No recipe enables it in this patch.

## Memory and lifecycle bounds

At the tested `MOTION_PRESSURE_GROW=0`, heap-key payload remains capped at 262144 bytes globally across co-bound archives. Fixed slab sizes/counts, slot tables, archive bodies, spill and pool heap margins, allocation failure handling and the four-binding limit are unchanged. Slabs are charged as metadata at binding admission, whether empty or occupied. A payload entering an already allocated slab increases useful-residency telemetry, not physical allocation. The maximum possible physical allocation is unchanged: the old policy could already reach its full heap-key cap while all reserved slabs were empty. This patch removes the extra restriction imposed when those slabs become occupied.

Logical `resident_bytes` and its peak keep their existing meaning and may now exceed the heap-key cap. Do not interpret that counter as physical heap-key occupancy or add it to metadata without subtracting occupied slab payload. The derived accounting adds no mutable counters or ABI/BSS fields. Ordinary inline archive bodies remain outside this key-pool budget, as before. Existing optional pressure-grow behavior is unchanged; this is not a new hard cap for a configuration that enables growth.

All new scans run within the loader's existing lock after its suspended-heap hold guard. Existing owner/lease pins, hold/suspend behavior, OOM eviction and retirement remain. Version3 bounded profiles still use exactly two reserved slabs, cannot spill or join the cold pool, and reject a miss while both slabs are pinned. This repair does not solve a recurring three-cold-clip working set in a strict two-slab profile.

## Verification

Run the asset-free regression from the repository:

```
python3 port/dreamcast/tools/d367/boss21/test_motion_pressure.py
```

The host harness includes the actual `native_motion.cpp`, substitutes only transport/allocation/KOS facilities, and generates synthetic valid FCV bytes. It tests baseline and enabled accounting, plus enabled accounting with the current lean lease path, under ASan/UBSan and leak detection.

The selected em12 hot-size contract totals 225184 bytes. Filling two already allocated 32416-byte slabs produces two evictions in the baseline control and zero evictions/zero new allocations with the candidate. Additional cases exercise aggregate co-bind pressure, actual acquire/release leases, all keys pinned, a poisoned suspended table, strict v3 no-spill, cold-pool and hot heap allocations, and one forced allocation failure through the actual OOM retry path. All pass. This reproduces the source accounting defect; it is not a new console thrash measurement.

SH-4 `native_motion.o` cross-compiles with the current QA motion-policy flags on base `6e0ee147a9ec975071d491bdab5636054b6b6f78`. After removing debug information, the baseline and knob-off objects have identical SHA256 `81d803db4c769d00a460b910df9e3b03f7e9dc9d42af789b1a6d879dbda31986`. Enabled code adds 174 text bytes and zero data/BSS bytes (text 8538 -> 8712; BSS 557 unchanged). Raw debug objects differ because source locations differ. See [the machine-readable receipt](motion-pressure-receipt.json).

This is target-object qualification only. A full linked QA program, knob-off program identity, actual post-s20 gameplay/I/O, menu/movie transitions, KOS reserve and physical-console acceptance remain integration gates. No new capture, timing, no-I/O or release claim is made. The patch contains no game payloads, profile edits or asset changes. The castle lane's additive `pl11-walk` row remains a separate dependency and must be preserved during integration.
