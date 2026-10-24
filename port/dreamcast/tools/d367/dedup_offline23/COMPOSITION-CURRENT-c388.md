# Merged-source composition rerun: c388020e9

PASS_HOST_COMPOSITION_ONLY at exact merged source
c388020e9f3add533196d0a86ab2fcef9460ea8d. The existing runner completed96 exact
host comparisons across8 configurations and detected the deliberately missing
cache-reset mutation. All eight complete-output hashes equal the prior04e1
control. No compatibility fix was needed.

The source snapshot /dev/shm/dedup-composition-source-c388020e9 contains208 source
files (2,443,185 bytes), each read directly from the requested Git commit rather
than the advancing main worktree. Its source-pins.json SHA256 is
30bb9ed4ce4058500d6eb3578bdc1936699799a3b15b93fba50cf39872c00376.
The actual runner and fixture bytes were verified identical to the copies in
c388: runner77c78a2d43fdb3d0b1905e1b59eba1a58f60fed41cccbfe42bf366ac9da6b004;
fixture b6480acabce30699e8feb022e7caad11c3a3a0d12ea1cfbfe543cc808dd94ed9.

[composition-controls-c388-host.json](/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/composition-controls-c388-host.json)
is the6,454-byte source/extraction/output receipt, SHA256
913e2df1d3820ad30bb832f565e05d7a38c72d1f3289ae84a49b530bd4644b95.
Detailed generated C++, binaries, traces and compiler logs remain only in
/dev/shm/dedup-composition-control-c388-r1. Core dumps and Python bytecode writes
were disabled. No SDK/target build, staging, guest, media or external STATUS edit
was performed.

The [control description](/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/COMPOSITION-CONTROL.md)
retains the method coverage, synthetic sequence, failure controls and arithmetic
limitations. This rerun covers SCENERY_DEDUP3 plus fresh/reused replay emitters,
submit-batch0/1, and the decoded-position reference. It executes actual extracted
production bodies and portable clipping with the documented SH4 instruction/SQ
adapters; it does not establish target rendering or hardware acceptance.

At c388, SCENERY_UV_SNAPSHOT defaults0 in scenery19.mk:70 and ACTOR_SETUP_LEAN
 defaults0 in game30.mk:2035; recipe.conf does not override either token. Their
preprocessor branches remain disabled in this host control. There is **no claim
for UV snapshot1 or actor setup1 composition**; actor setup itself is outside the
emitter test. Runtime/defaults are unchanged. Private QA-pair packaging and
release-derived memory qualification remain main's separate work.

Rerun command, using a new RAM output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm \
python3 port/dreamcast/tools/d367/dedup_offline23/check_composition.py \
  --source-tree /dev/shm/dedup-composition-source-c388020e9 \
  --expected-source c388020e9f3add533196d0a86ab2fcef9460ea8d \
  --output /dev/shm/a-new-c388-composition-control
```
