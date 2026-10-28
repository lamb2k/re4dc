# Build 31: portal culling and world part plan

**2026-10-28 progress 1: DONE** conservative portal builder, fixture graft and 21 synthetic tests; **NEXT** qualify `WORLD_PORTAL29` runtime and `WORLD_PART_PLAN29`; **BLOCKED** private room geometry and console acceptance are Claude's runs below.

Branch: `codex/world-portal-part-plan-20261028`. Final integration base for
this step: `a3320b546e5d7936d35a1975b02f0eacb9002600` (`origin/t15/int`),
refreshed immediately before push. This first commit contains tools and
documentation only; runtime changes are a separate, independently qualified
step. The queue and release recipe are unchanged.

## Step 1: candidate cells, no runtime enablement

The default-off `--barn-portals29=1` builder accepts a hash-bound R4IM v3,
R4PW and R4ID package and explicit geometry-authored building/eye boxes.
It starts every face open, subtracts only exactly coplanar opaque static
wall triangles, and intersects coverage across every stored LOD. Exact
rational polygon complements preserve cracks; unsupported or uncertain
surfaces remain openings. Apertures expand by at least 64 mm and round
outward. Complex faces become wholly open instead of exceeding the runtime
portal budget. This supports multiple buildings in any explicitly named room.

The output retains PCL2 storage and adds a CRC-bound `WP29` witness trailer.
Legacy loaders reject its extended size. The upcoming runtime must verify
current-view opaque submission and source state; merely having wall data in
a package grants no hiding permission. The graft tool verifies matching
staged mesh/policy identities and adds only the candidate cell reference to a
new fixture. Neither tool reads inputs or writes output with its flag absent
or zero.

Proof and exact schema: [PORTALS29.md](../../../tools/d367/ps2world/interior/PORTALS29.md).
The 21 tests pass on actual synthetic package serialization: door/window,
0.125 mm crack, LOD openings, dynamic/cutout/wrong-facing walls, multiple
houses/rooms, safe-eye/near refusal, CRC/hash/malformed inputs, legacy loader
exclusion, fixture identity and disabled no-output behavior. No game assets
are included.

```sh
python3 -B port/dreamcast/tools/d367/ps2world/interior/test_barn_portals29.py -v
```

Tool-only release identity follows directly from the changed-file scope:
no runtime, build recipe, header or generated asset changes are committed
in this step. Warm/cold-I cycles, loads/stores, 32-byte data lines, runtime
code/stack and resident bytes added by this step are all **0**.
**MODELLED whole-frame delta: 0 ms.** Cell file size is reported by the tool;
runtime costs and benefit remain separate evidence.

## Exact private-data commands for Claude

From the repository root, set `PKG` to the actual staged room-package
directory, `CFG` to the geometry-authored config described in PORTALS29.md,
`BASE_FIXTURE` to a fixture explicitly staging that mesh and policy, and
`OUT` to a fresh private result directory. Do not use the explanatory
coordinates in the schema as r103 geometry.

```sh
sha256sum "$PKG/ps2-world.re4mesh" "$PKG/ps2-world.r4pw" "$PKG/ps2-world.ids"
python3 port/dreamcast/tools/d367/ps2world/interior/barn_portals29.py \
  --barn-portals29=1 --config "$CFG" --package "$PKG" \
  --out "$OUT/interior.cell" --report "$OUT/portal-proof.json"
python3 port/dreamcast/tools/d367/ps2world/interior/graft_portals29.py \
  --barn-portals29=1 --fixture "$BASE_FIXTURE" --cell "$OUT/interior.cell" \
  --out "$OUT/fixture-portals29.json"
```

Retain package/config hashes, face coverage/openings, witness identities,
refusal output and candidate bytes. Runtime build/QA commands follow in the
next qualified step. Do not enable an old PCL2 runtime against this candidate.

## Questions

1. Please author safe eye/hull boxes from the actual r103 opaque PS2 walls,
   then return the generated proof report (or exact refusal). Which witness
   parts occur before the outdoor targets in submission order?
2. Return the outward/inward barn `WORLD_METER`, DFA and DSA windows with
   matched image/package hashes. Proposals 2, 4 and 5 remain notes pending
   those measurements.
3. On the runtime candidate, Claude must run the magenta hidden-geometry
   walk, missing/stale/heap refusal cases, doors and near-plane crossings,
   leave/reentry, s30 loan/return, full disabled image identity and STRICT
   gameplay. No private or console PASS is claimed here.

## Answers (Claude)

Pending.

## Answers (owner)

2026-10-28 Codex owner: tool-only step merged as `ebb7668d` onto
`origin/t15/int`. The 21 committed synthetic tests pass locally. The current
release recipe builds with `rc=0`, `missing=0`; ELF SHA-256
`6468e3e08405f99474f8161ee0c6ab965ff8e11b8b97debf4e11117010f31446`.
No runtime/build/recipe inputs changed, so this step adds no enabled switch
or console speed claim. Runtime work remains open; continue qualified small
commits rebased onto the latest integration branch.

1. Safe eye/hull boxes and witness submission order remain an owner private
   geometry task. No geometry-authored config or proof report is available
   in this hand-back; explanatory schema coordinates will not be used as
   r103 data. The exact builder/graft commands above remain pending those
   pinned private inputs, rather than receiving a synthetic private PASS.
2. Matched outward/inward console windows remain pending the user's slot
   154 ALL ON DIAG / slot 151 baseline session at the same teleported spots,
   with the console dialled onto the Pi link. Existing handover readings
   are historical and do not satisfy this matched package/image request.
3. Runtime, magenta walk, refusal, near/door crossing, reentry, s30, disabled
   image identity and gameplay gates remain pending the runtime candidate.
   This tools-only step cannot qualify or enable the legacy PCL2 runtime.

Watcher cadence is now every five minutes per the user's latest instruction.

2026-10-28 18:06 EDT follow-up: `92f7cf811` arrived while the first tool
landing was being recorded, with the original tools rebased as `0efd3ee31`.
The fresh integration merge conflicts (add/add) only in this hand-back file.
The merge was aborted; no follow-up runtime code was landed or enabled.
Please rebase/re-sync onto current `origin/t15/int`, retain the landed tools
and Answers (owner), qualify again, and push. The owner will retry on the
five-minute watch; no manual conflict resolution is authorized.
