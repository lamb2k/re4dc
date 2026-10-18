#!/bin/bash
# ch5regen: lane-private copy of the harness stager (unchanged files, RE4DC_HARNESS) with the recorded island arms
# (cx76mW / cx80mW / cx79mW program files from the ch5found16 harness clones on C:). Base = the stager's base path
# (now the Test 16.3 disc a61dfc16). Nothing in the shared harness is modified.
set -euo pipefail
SH="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927"
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018
R=$E/hroot; H=$R/h
E5=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
mkdir -p "$R/integration-source-r11" "$R/renderer/inventory-uiorder-r1" "$H/stage-ext4" "$H/programs" "$H/scenarios"
cp "$SH/integration-source-r11/MEDIA.json" "$R/integration-source-r11/"
cp "$SH/renderer/inventory-uiorder-r1/stage-iso.py" "$R/renderer/inventory-uiorder-r1/"
P="$SH/playability-r11-r1"
cp "$P/stage-scenario-copy.py" "$P/stage-scenario.py" "$P/run-emulator-novsync-i26.py" "$H/"
cp "$P/stage-ext4/stage_scenario.py" "$P/stage-ext4/disccache.py" "$H/stage-ext4/"
python3 - "$H" "$E5" <<'PY'
import json, sys, shutil, os, hashlib
H, E5 = sys.argv[1:3]
out = {}
for c, arm in (('h-cx76mW', 'candidate-routecx76mW'), ('h-cx80mW', 'candidate-routecx80mW'), ('h-cx79mW', 'candidate-routecx79mW')):
    src = json.load(open(f'{E5}/{c}/programs-route.json'))[arm]
    d = f'{H}/programs/{arm}'; os.makedirs(d, exist_ok=True)
    for n, m in src['files'].items():
        s = f'{E5}/{c}/programs/{arm}/{n}'
        assert hashlib.sha256(open(s, 'rb').read()).hexdigest() == m['sha256'], (arm, n)
        shutil.copy2(s, f'{d}/{n}')
    shutil.copy2(f'{E5}/{c}/programs/{arm}/syms.txt', f'{d}/syms.txt')
    out[arm] = src
    print(arm, len(src['files']), 'files ok')
json.dump(out, open(f'{H}/programs-route.json', 'w'), indent=2)
PY
sha256sum "$H/stage-scenario-copy.py" | cut -c1-16
cmp "$P/stage-ext4/stage_scenario.py" "$H/stage-ext4/stage_scenario.py" && echo stager-identical
