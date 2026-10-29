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
