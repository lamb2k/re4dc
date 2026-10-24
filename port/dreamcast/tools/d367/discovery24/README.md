# Discovery24: ranking only

This read-only host tool uses three authenticated frame647 camera eyes (hut,
turn, walk), the entire eligible unconditional opaque PS2 scene at the exact
existing R6 baked-pose host-replay selected LOD **full-authored envelope**, and real parity-correct indexed
triangles. It does not use the old512face/20pair search cap.

For each eligible selected whole-cluster target,27 lo/mid/hi box samples cast
nearest-hit rays, excluding **all** source triangles in the same physical
placement/cluster. Counterfactual selected whole-meshlet boxes exclude that exact
meshlet and are explicitly unsupported by the current cluster-PVS namespace.
Each nearest hit retains physical placement, source field/rawowner, part/material,
cluster, selected level, meshlet, triangle ordinal and actual corner indices.
A separate declared second source pass repeats whole-cluster rays using only
strictly earlier physical placements. Its rays count toward the same global110k
cap; this reveals earlier sources hidden behind a nearer late source. Placement
order is a prerequisite, not an actual committed renderer-prefix receipt.
Connected patches use shared actual cache indices within one meshlet only; no
position welding, flattening, convex hull filling or cross-LOD unions.

All-fixed-sample hits are **only hints**, including when a single connected patch
hits every sample. The off-centre-hole control demonstrates27 hits with a real
unsampled hole. No certificate, renderer admission, gain or performance claim is
produced. Near hits, source edge contact, prefix order, patch boundaries and
missing actual material/emission/numeric/raster receipts remain blockers. Source
cull metadata is retained, not reinterpreted as a confirmed camera-facing draw.

The eye is an exact rational inverse of12 recorded f32 view words, converted to
double for approximate discovery. Complete historical projection prefix is
retained but unused. No truncated VP/projection tail is reconstructed. Historical
capture programme/profile and host replay are labelled separately; replay LOD is
not observed actual played LOD or current runtime geometry emission. Some replay
meshlet counts are clipped subsets; the selected LOD is directly authenticated,
and the full authored level is used without inventing a clipped identity roster.
The first run refused an incorrectly strict whole-level count assertion before
ray work; its private log is retained and the assertion corrected to extent
validation. This envelope can include clipped sources, an explicit blocker.

## Bounded invocation

From the repository root, with a new private output outside the checkout:

```
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python3 -B port/dreamcast/tools/d367/discovery24/rank.py \
  --source-tree "$PWD" \
  --r6 /mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/I001-fb254-lod-surface-r6 \
  --out /dev/shm/interior-discovery24-r1/report.json
```

One process/numeric thread, hard address-space cap256MiB, max200,000 triangles
per full selected scene,110,000 total rays across all three cameras,16MiB full
private report. Any limit refuses rather than silently truncates. It authenticates
R6 report, original/current physical ownership, all input hashes, actual texture
package, profile/source policies, raw camera logs, replay hashes and namespaces.
The output is exclusive. It emits no PVS/table/assets and changes no renderer.
No game/private geometry, cameras or payloads belong in Git.

Controls: `cd port/dreamcast/tools/d367/discovery24 && python3 -B -m unittest -v test_rays`.
Twelve focused controls cover positive plane, centre/off-centre holes, false corner
inference, sliver, near, self-cluster/let exclusion, nearest choice, provenance,
unsupported LOD/namespace, hard budget/index refusals and256BVH-versus-complete
naive nearest-hit comparisons. Component triangle ordinals and source corner
indices are retained, alongside actual part/material/source-cull metadata. Synthetic coordinates
are mathematical controls, not game certification.
