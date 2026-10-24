#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/stat-bytes23-complete
L=/root/work/lanes/stat-bytes23-land
R='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/REVIEW-MENDEZ-CAMERA.md'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
[ -s "$R" ]
[ ! -e "$L" ]
[ -z "$(git -C "$B" status --porcelain)" ]
git -C "$B" fetch origin t15/int
[ "$(git -C "$B" rev-parse origin/t15/int)" = 933936ea7f45ba81c09277a780ed00111407aa23 ]
git -C "$B" worktree add -b wip/stat-bytes23-land-20261023 "$L" origin/t15/int
git -C "$L" merge --no-ff 2a14662d4b025031cd93f64eed6a5d8159d473b7 -m 'Merge the complete STAT routine-byte audit unit'
python3 - "$L" "$E" "$R" <<'PY'
import pathlib,sys,json
p=pathlib.Path(sys.argv[1]);e=pathlib.Path(sys.argv[2]);review=pathlib.Path(sys.argv[3])
d=json.loads((e/'mendez-bounded-r3-route-results.json').read_text());assert all(x['room10f'] and x['deaths']==2 for x in d.values())
r=p/'port/dreamcast/tools/d367/rr/recipe.conf';s=r.read_text();lines=s.splitlines(True)
ix=[i for i,x in enumerate(lines) if x.startswith('CH2="')];assert len(ix)==1;i=ix[0]
assert 'STAT_ROUTINE_BYTES=' not in lines[i] and 'STAT_DIAG=' not in lines[i]
lines[i]=lines[i].rstrip('\n')[:-1]+' STAT_ROUTINE_BYTES=1"\n'
lines.insert(i,'# 2026-10-23 (stat-bytes23): enable the complete routine-word audit, including VMU boat ammo;\n# OFF main/14 overlays identical; H2 340/340 heap_before93920, KOS, GDEMU1, 27-room census, bell and Mendez gates.\n# Mendez camera line-note delta is isolated to the corrected moved predicate; no gameplay drift. STAT_DIAG stays off.\n')
r.write_text(''.join(lines))
r=p/'README.md';s=r.read_text();anchor='## Coming soon: Test 23';assert s.count(anchor)==1
bullet='- [x] **Boat weapon display:** boarding the boat shows the harpoon and hides handgun ammunition.\n'
assert bullet not in s
start=s.index(anchor);end=s.index('\n## ',start+len(anchor));section=s[start:end];assert '- [x] **Mendez keeps fighting' in section
s=s[:end]+'\n'+bullet+s[end:];r.write_text(s)
docs=p/'port/dreamcast/docs/qualification';docs.mkdir(exist_ok=True)
(docs/'STAT_ROUTINE_BYTES_20261023.md').write_text('''# STAT routine-byte audit qualification\n\nSource unit: 2a14662d4b025031cd93f64eed6a5d8159d473b7, based on integration 933936ea7f45ba81c09277a780ed00111407aa23. Default-off STAT_ROUTINE_BYTES is enabled only in this qualified release recipe. STAT_DIAG remains zero in production. The independent EM35/Ganado knobs remain unchanged.\n\nThe unit repairs 62 production source lines and seven routine macros, with the VMU canonical-word consumer included. OFF raw programme and all 14 overlays match baseline exactly. Raw programme SHA256: OFF dba997478ac575140777e60507d854e2138bdfcabe7d546af75758ca0f64a6ab; ON 0745d16c39fcc08dee3afb7d0d1ce473379387190a93b395aa8c4358dad741a2. Assets retain the same 1,712-file release manifest a424cdc4f68460b0d5ea8f591c44c62eefeab85b67941410bc996680dce41547.\n\nSource/host: independent representation audit and exhaustive local byte/macro controls pass; no fresh PS2 executable oracle was acquired. Target: actual SDK builds/link/overlay identity checked; SDK archive unchanged. Flycast console mode: matched H2 s30 340/340, restored1, heap_before93,920 each; 48KiB KOS headroom6,112/6,176; GDEMU seed1; census/TEXCHK/character checks27/27. Bell2,857 matched required-field ticks, zero actor movement drift.\n\nMendez: both source damage/death forms, full s02/s10/s11, False Eye acknowledgement, normal window event and actual room10f exit in about45seconds. The raw2,643-tick comparison remains MUST-DIFFER for19 line-query-note fields only. A one-line legacy camera-predicate control restores MUST-IDENTICAL against OFF. All other required fields match; zero player/enemy movement drift. This is an attributed correctness change, not a strict trace-identity claim. See the independent camera review.\n\nThe actual boat routine is authenticated in both arms. OFF incorrectly shows handgun ammo; ON shows the harpoon with no gun ammo. Stills are intentionally different and asynchronously posed, so full-frame identity is not claimed. VMU target consumer is source/compiled verified; LCD console behavior remains prospective.\n\nPrivate QA: RE4DC-QA23-StatBytes-2a14662d, raw bfb586d0fc8034ef6c4a1b385e93a837eec6d0addecce157e49f9eef91fcf4bc; QA_MENU1 STAT_DIAG1 PC_SAMPLER0. Its own boot/menu-warp/H2/GDEMU1 pass; QA heap_before48,768 differs from production. Full-release and physical Dreamcast acceptance are not claimed. Later omitted rooms/enemies are source-reviewed only.\n\nPrivate logs, screenshots, manifests and exact programmes: C:/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d. Public support-tools branch: wip/stat-bytes23-evidence-tools-20261023. Never merge or ship the separate camera-control branch.\n''')
(docs/'STAT_MENDEZ_CAMERA_REVIEW_20261023.md').write_bytes(review.read_bytes())
PY
git -C "$L" diff --check
git -C "$L" add README.md port/dreamcast/tools/d367/rr/recipe.conf port/dreamcast/docs/qualification/STAT_ROUTINE_BYTES_20261023.md port/dreamcast/docs/qualification/STAT_MENDEZ_CAMERA_REVIEW_20261023.md
git -C "$L" commit -m 'Enable the qualified STAT routine-byte unit in the release recipe'
git -C "$L" fetch origin t15/int
git -C "$L" merge-base --is-ancestor origin/t15/int HEAD
[ "$(git -C "$L" rev-parse origin/t15/int)" = 933936ea7f45ba81c09277a780ed00111407aa23 ]
git -C "$L" push -u origin HEAD:refs/heads/wip/stat-bytes23-land-20261023
git -C "$L" push origin HEAD:refs/heads/t15/int
git -C "$L" rev-parse HEAD