# Bounded prepared skin-table reuse

`ACTOR_TABLE_REUSE14=1` requires `ACTOR_TRANSACTION=1`,
`NATIVE_ACTOR_FAST=1` and `ACTOR_SKIN_OWNER_POOL=0`. It defaults to zero;
only `platform/native_actor_fast.o` receives its definition. Existing
recipe/presentation exclusions and grouped-emitter prerequisites are unchanged.

`prepare_frame` and `one_frame` can retain A's prepared table across B only
inside one live shared-table skin lease and render-workspace epoch. The cache
checks its current serial, source frame, palette/source bindings, array counts,
quantization and existing exact view key. Directions still follow the existing
per-light fold checks. Acquisition, release and primitive retirement keep their
existing complete Frame invalidation.

All charged table bytes, including holes left by Frame victim reuse, must fit
within `owned_workspace.maximum()`. Thus retention does not lower the existing
scratch limit or enlarge any workspace/reservation. Capacity failure or unknown
ownership takes the old single-table reset; unretained source Frames preserve
the original same-info hit policy. Nothing reorders source, translucent or
material runs. Two unsigned fields are added to each of the existing four
Frames when enabled; no geometry, palette or workspace capacity is added.

Run with new output directories:

```sh
python3 -B port/dreamcast/tools/cloud/table_reuse14/host.py --output "$HOST_OUT"
python3 -B port/dreamcast/tools/cloud/table_reuse14/host.py --output "$SAN_OUT" --sanitize
python3 -B port/dreamcast/tools/cloud/table_reuse14/identity.py --output "$OFF_OUT"
```

The whole production actor TU runs through the established hosted AVK ABI and
SQ adapters. Test-only counters instrument actual table/matrix builders. Real
workspace/skin acquisition and release publish synthetic source bindings; the
reservation uses the existing max-role `align32(palette_count*114)` contract.
A third live role permits smaller A/B tables to fit that same reservation.
The tight profile has only A/B, so retention must fall back.

Ordinary and grouped A-B-A, both light layouts, current view/light changes,
pose replacement through a fresh lease, release/retirement/rebinding, original
unknown-owner hits, tiny storage and victim pressure are covered. OFF and ON
compare every emitted word. Pinned whole hosted-TU preprocessing/objects match
at absent/zero; actual primary Make dry-runs check scope, dependencies, expanded
selectors/whitespace and recipe0/1 composition.

These are public source and host checks. SH4 codegen/stack/full-image OFF,
current private incidence, complete memory, matched full cost and console/look
acceptance remain separate gates. Builder-count reduction is not timing data.
