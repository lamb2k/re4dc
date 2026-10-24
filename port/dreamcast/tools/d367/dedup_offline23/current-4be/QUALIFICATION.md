# Current 4be dedup qualification — root review pending

Source: 4be08e0110592510e3630c01fa9f49b3ac2fed3d.
Baseline: d5c1ceab9e06461462669b3ce1d28a379747a74a.
Root pushed and verified origin/wip/dedup-offline23-current-d5c-20261023.
Production integration/recipe still awaits root decision. This lane changed
only owned helpers/documents during current qualification; no runtime edits.

Both private normal QA folders are sealed for independent root review:
- C:\Game Dev\Emulators\RE4DC-QA23-Dedup-Off-4be08e01
- C:\Game Dev\Emulators\RE4DC-QA23-Dedup-On-4be08e01

Each contains gdemu/disc.gdi and three final tracks, README.txt, STEPS.txt,
IDENTITY.json, SHA256SUMS.txt and the retained menu controls guide.
They remain marked root-review/physical-acceptance pending. No ZIP, SD copy,
publication or private-pair-ready acceptance was performed.

Both arms retain original DATA29, all 41 texture assets and the same four
frozen compact alternates. OFF0 reads originals; ON3 selects the alternate.
Final file manifests differ only in main programme and 14 overlays. Original
geometry, UV/color, LOD/source identities and baseline files are retained.
Normal QA knobs only: QA1/PC0, no KOS/squeeze/census diagnostic contamination,
arena0, current four audits ON, select-only/replay/batch ON.
SCENERY_EMIT_PREFETCH=0 and SCENERY_SELECT_LEAN2=0. The independently found
PREFETCH1 context defect is outside this profile and is being repaired separately.

Final GDI track03 SHA256:
OFF 52d2c05d1fa37d5d72546bb560cb317048540eb5ae1e97d6ae350aba9a0dc2a5
ON  e09cc566770513cd53647a7429d0f7f992fe5d6718e82a8bd960d6effb8d5920
Both pass loader/standard lint, independent full track and all-file readback,
and a second final readback after their checks. Native sha256sum -c verifies
every delivered file against each SHA256SUMS manifest.

Six actual bounded console-mode QA checks pass:
- Final standard GDI boot, four PID-targeted key steps and R100 entry:
  OFF 22.6 seconds / ON 22.6 seconds.
- Separately labelled, exact same programme/all14/data fixture proxy:
  menu diagnostics/QR flow, soft reset and R103 entry, OFF 14.6 / ON 14.7 seconds.
- Same proxies, full H2: OFF 32.9 / ON 34.1 host seconds; all 1465/571/340
  frames decoded/uploaded/presented, arena restored=1. Normal QA s30 heap:
  OFF 48,768 / ON 98,496 bytes (+49,728). This is separate from standard
  programme memory and does not establish hardware timing.

After each arm's three checks and fresh final readback, only its newly created
proxy track03.iso backing was retired with exact resolved path, full hash,
nlink=1, guest-lock/no-owned-Windows-guest and deletion manifest checks.
All final media, proxy metadata, IP/manifests, source/ELFs/overlays, fixtures,
logs, captures and screens remain. Earlier media/evidence were not pruned.
The 4.5 GiB media reserve and 24 GiB stage floor were respected.

Existing standard-profile gates remain:
- Fresh OFF release main/all14 equals actual d5c production; raw SHA
  49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b.
  ON raw 1077a1386ac3431b97d069291424a14117adf55f267aff78fbedf166bdc6df09.
  Full-play twins reproduce their own releases, main/all14.
- Standard H2 all 1465/571/340 uploaded/presented, restored=1; heap
  OFF 93,920 / ON 139,552 (+45,632), compact loan 1,512,928 and reload observed.
- All eight KOS 48 KiB challenges pass; minimum headroom >=4,096.
- Required TEN actual GDEMU seeds pass exact environment/profile, read/landing
  witnesses, door103 endpoint and bad-read/deadline checks. The earlier
  seed-1-only completion claim was corrected explicitly and preserved.
- Scoped enabled CAST-GC/TEXCHK/LEON/VRAM checks pass. r100 allocator retries=2,
  evicted=11 are retained; observed refusal/guard/nocontig fields are zero.
  No all-actor or all-material completeness claim.
- Bell 2,866 and Mendez 2,692 common decision ticks MUST-identical, zero drift,
  using byte/data/fixture-authenticated reused OFF-equivalent captures.
  Bell decodes 1,331 but uploads/presents 1,318 (reference 1,313).
- Explicit FPS=yes held cross/farm/forest stills match both buffers exactly.
  This is scoped visible held-frame evidence, not all-frame actor state.
  Earlier watchdog/implicit-default attempts remain preserved.
- Host 28 tests, 96 composition cases plus mutation, three-room binding and
  12 reader controls pass. Scope is PREFETCH0 / LEAN2=0.

Known baseline Mendez late-pair material issue remains. Root's separate private
PS2 upload repair is not included or admitted; its visible use is unproven.
Physical-console acceptance and hardware performance remain pending.

Evidence root:
C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023\current-4be08e01
Final seal: private-qa-pair-seal-r1.json
SHA256 4180931954be3dc47e587bea96b82a550799c898a7491a9de4df5e01a69f95be
Independent checksum readback: qa-delivery-checksum-readback-r1.json
SHA256 3d6fdd9c846792cf297b3e2ca061bca516695e81d0f610aca74f3fc0ce3e763f
Other bounded receipts: qa-media-r1/pair-media-identity.json, six capture
qa-gate.json files, qa-{off,on}-proxy-retirement-r1.json, and
qa-capture-inventory-r1.json (24 PNGs; inventory only, no wall-time pixel claim).

Prior failed 5be OFF98,016/ON93,920 and successful compact712/current4be
captures/source snapshots remain unchanged. I-001 stays queued until actual
root landing. After that notice, the authorized offline estimate proceeds
without another coordinator wait.

