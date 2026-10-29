# EF06 first upload-incarnation slice

`PS2_UPLOAD_INCARNATION=1` adds a four-byte uint32 token to each texture Entry
and each PS2 header slot. It is independent of UI_HANDLES. Retirement revokes
it before callbacks; successful publication advances it after upload/retries.
The single Entry publication site is in load(); all Entry closes use close_entry.
Source-table resets and movie/room transitions never reinitialize the Entry array.
At uint32 exhaustion zero permanently disables derived-header reuse for that
Entry, while uncached compilation/drawing remains available. No token reset or
whole-cache flush can revive an earlier incarnation.

Ordinary header reuse, SCPS direct hints and the opaque readiness predicate
compare the stored upload token. Existing key, size, pass/cull/fog, Entry validity,
address, representation/dimension and full readiness-word comparisons remain.
Unknown/refused state retains its ordinary conservative behavior. This is a
correctness correction; no runtime saving or console result is claimed.

Run from the repository root, using fresh output directories:

```bash
python3 port/dreamcast/tools/cloud/build34/upload_host.py --output "$OUT/host"
python3 port/dreamcast/tools/cloud/build34/upload_host.py --sanitize --output "$OUT/sanitized"
python3 port/dreamcast/tools/cloud/build34/build_controls.py \
  --baseline 9ee386e3ef8d46bcd7ae8586d2064cd1ae22864e \
  --config port/dreamcast/tools/cloud/build34/upload_profiles.json \
  --output "$OUT/target" --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" \
  --sdk-root "$SDK_ROOT" --toolchain-receipt "$TOOLCHAIN_RECEIPT"
```

The host gate extracts actual Entry, close_entry, accepted publication,
Ps2HdrSlot/fill and exact ordinary-hit, SCPS and readiness predicates from
native_ui.cpp. Controlled Package/PVR edges model same-address format/mip
replacement and identical replacement. It checks refusal while closed, fresh
refill, effective-key/mode/size/address guards and permanent exhaustion. Both
UI_HANDLES settings run. OFF reproduces six stale-header counterexamples per
setting; ON rejects them. ASan+UBSan inspect host boundaries; leak inspection
is disabled. These are actual-source cache boundary fixtures, not full loader,
GPU fence, actual room/movie replay, visual/STRICT or physical timing tests.
The target profile remains separate evidence. Full programme/overlay OFF
identity and live lifecycle/look/gameplay qualification belong to integration.

## 2026-10-29 completed evidence

Runtime commits: `5f057b2ea` and OFF formatting followup `0efa52fe8`.
Host and ASan+UBSan each pass 404 assertions across four compositions, plus
actual Make-hunk default0/explicit0/1 acceptance and five invalid-value refusals.
Public sanitized receipts: [host](receipts/upload-host.json),
[sanitized](receipts/upload-sanitized.json), [target](receipts/upload-target.json),
[disabled identity](receipts/upload-disabled.json).

The current local release chain, rather than an unavailable independently bound
cloud SDK, built fresh baseline9ee386e3, candidate absent, explicit0 and ON arms.
All four real build logs return rc0 and have nonempty ELF and existing empty
missing.txt. Compiler is SH-4 GCC15.2.0; KOS804b3195; sh4zam33fa4850.
The exact serialized runner is `codex-lanes/engine-wave1/ef06-build-v2.sh` in the
Windows workspace; outputs/logs are under
`/root/probe/engine-ef06-20261029/release2` and
`/root/probe/lanes/route/out-ef06oct29v2{baseline,absent,zero,on}rP`.
It sources unchanged rr/recipe.conf, then uses K/T/LP and CH2 overrides with
ch2-build.sh rP. Each unique output was checked absent before route-build.sh
could remove it. ROUTE_PROGRAMS_DIR was private to the gate and
ROUTE_PROGRAMS_JSON was empty. No image mastering or shared registry update.

Baseline==absent==explicit0 for the 3,372,036-byte raw programme
(SHA256 `fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1`),
all15 overlay payloads and all11 allocated ELF sections including zero-fill
metadata. Whole debug ELFs differ. The actual Make-derived native_ui TU also
matches byte-for-byte for complete -E -P preprocessing (1,491,094 bytes) and
-g0 object (416,832 bytes) in all three controls.

The enabled full release links. Additional production TU compiles using the
actual release command with explicit last forced-header overrides pass:
headercache1/UI_HANDLES0; SCPS1/headercache2/batching0; and
PVS1/headercache1/SCPS0/batching0 readiness. These three are TU compile checks,
not separately Make-derived whole-profile link claims. The inherited batch1
PVS attempt correctly refused its existing exclusion before the batch0 compile.
The optional full Make profile JSON uses batch0 for readiness too.
Enabled release allocated BSS grows 2,048 bytes at this 128-set header table
(512 slots, +4 bytes each); Entry fits prior padding in this configuration.
Rounded linked _end grows from8c4170d4 to8c4178d4. This is storage evidence,
not runtime headroom, stack bounds, hardware duration or speed acceptance.

No resurrection audit: there is one static Entry array declaration; no Entry
array memset/memcpy, replacement assignment, placement construction or runtime
reinitialization exists. The only Entry valid publication is the guarded
load() success site. Its direct package retries/failed closes are unpublished;
all published retirement/eviction paths use close_entry. Room retirement
preserves resident entries by aging frame or calls close_entry; source/movie
boundaries never assign the token back to1. Actual live lifecycle/GPU behavior
remains a separate acceptance gate.

Reusable full-output comparison (no knob normalization; caller separately binds
its exact common resolved recipe fields):

```bash
python3 port/dreamcast/tools/cloud/build34/upload_compare.py \
  --baseline "$BASE_OUTPUT" --arm "$ABSENT_OUTPUT" --arm "$ZERO_OUTPUT" \
  --output "$OUT/upload-disabled.json"
```
