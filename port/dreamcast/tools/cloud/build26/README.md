# Build 26 public qualification

The hand-back is in `port/dreamcast/docs/cloud/BUILD26_DRAW_FALLBACK_AUDIT_20261028.md`.
This directory contains source-bound receipts and reproducible public fixtures,
not private chapter data or a complete linked game image.

## Target identity and composition

From the repository root, provide the pinned Dreamcast compiler, KOS and
sh4zam trees and the compiler restoration receipt. The gate checks their
versions and hashes against the inherited Build 24 toolchain receipt.
Use new output directories; the scripts refuse to overwrite an earlier run.

```sh
python3 port/dreamcast/tools/cloud/build26/build_controls.py \
  --output /tmp/b26-target \
  --sh4-cxx "$B26_CXX" --kos-root "$B26_KOS" --sdk-root "$B26_SDK" \
  --toolchain-receipt "$B26_TOOLCHAIN_RECEIPT"
```

The baseline is pinned to `9a66e3fce8899f69378f12b5f9517f297f1fa314`.
The gate compares complete preprocessed bytes and complete target objects
for ten changed existing translation units, QA_LINK off/on, and each new
control absent, individually zero, and jointly zero. Debug records and line
markers are excluded consistently. Enabled compositions compile the actual
sources and resolve the new audit hooks in a relocatable link. This does
not substitute for full private-image identity or console qualification.

The public profile explicitly uses `NMR_POOL_LOD=0` in both arms because the
selected chapter-2 LOD data is private. No release recipe is changed.

## Numerical fixtures

Each command executes compiled SH-4 instructions from the actual production
core or stated production window. The scripts and receipts specify excluded
work. Cold-I figures use a synthetic linked layout; data-cache misses and
device/SQ waits are not predicted.

```sh
python3 port/dreamcast/tools/cloud/build26/counter_cost.py \
  --output /tmp/b26-counter \
  --sh4-cxx "$B26_CXX" --kos-root "$B26_KOS" --sdk-root "$B26_SDK"
python3 port/dreamcast/tools/cloud/build26/world_source_cost.py \
  --output /tmp/b26-world-cost \
  --sh4-cxx "$B26_CXX" --kos-root "$B26_KOS" --sdk-root "$B26_SDK"
python3 port/dreamcast/tools/cloud/build26/actor_front_cost.py \
  --output /tmp/b26-actor-cost \
  --sh4-cxx "$B26_CXX" --kos-root "$B26_KOS" --sdk-root "$B26_SDK"
```

`compact_receipt.py --input RAW.json --output NEW.json` removes repeated
command strings while preserving numeric traffic, source hashes, identity
results and a hash of the raw receipt. It does not turn these bounded windows
into full-game measurements.

## Host contracts

```sh
python3 port/dreamcast/tools/cloud/build26/qa_contract.py \
  --sanitize --output /tmp/b26-qa-host
python3 port/dreamcast/tools/cloud/build26/model_clip_host.py \
  --sanitize --output /tmp/b26-actor-host
python3 port/dreamcast/tools/cloud/build26/world_host.py \
  --sanitizer --output /tmp/b26-world-host
python3 port/dreamcast/tools/cloud/build26/world_audit_sites.py \
  --output /tmp/b26-world-sites
```

The QA contract exercises the counter lifecycle, every reason, saturation,
actual row/framing functions, bounded T-part backpressure/retry/cancellation,
pending-snapshot isolation and the actual telemetry function's page retention.
World checks compare the production emitter's status and packet bytes.
Actor checks compile the actual translation unit in four clipping
compositions, compare synthetic output and verify APLAN reason mappings.
Host scalar equality does not establish SH-4 FTRV/reciprocal boundary identity.

Claude still needs the chapter-1/2 reason census, matched visual/gameplay
captures, full-image gates, real heap/VRAM checks and hardware timing before
ranking or enabling the candidate fixes.
