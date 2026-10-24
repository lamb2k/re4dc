#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/dedup-offline23-land
T=$TREE/port/dreamcast/tools/d367
O=/root/probe/lanes/route/out-rs24fb254camrW
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
HOST='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/restrip23-fb254/root-forest-camera'
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
[ "$(git -C "$TREE" rev-parse HEAD)" = fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
exec 7>"$E/guest.lock";flock -n 7 || exit 2
[ ! -e "$E/capture-r1" ]
python3 - "$E" "$O" "$OWN" "$HOST" <<'PY'
from pathlib import Path
import hashlib,json,sys
e,o,own,host=map(Path,sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((e/'PROGRAMME-PINS.json').read_text())
for n,pin in j['files'].items():assert sha(o/n)==pin['sha256']
p=json.loads((e/'CAPTURE-HELPER-PINS.json').read_text())
assert sha(own/'forest-freeze800-capture.py')==p['generated_sha256']
assert sha(host/'census-bound-run.py')==p['bound_sha256']
assert sha(host/'stat_owned_ram.py')==p['ram_backend_sha256']
assert sha(own.parent/'world-emit23/current-stills/force_limited.py')==p['force_limited_sha256']
b=json.loads((e/'base/base.json').read_text());assert b['elf']==str(o/'re4dc-game.elf')
track=e/'base/track03.iso'
assert sha(track)==(e/'base/track03.sha256').read_text().strip()
(e/'BASE-BINDING.json').write_text(json.dumps(dict(programme_pins_sha256=sha(e/'PROGRAMME-PINS.json'),base_metadata_sha256=sha(e/'base/base.json'),base_manifest_sha256=sha(e/'base/base-manifest.json'),actual_track_sha256=sha(track),fixture_sha256=sha(e/'forest-camera-fixture.txt'),scope='Current source diagnostic only: PVS mode2, batch0, explicit limited console. No current-performance comparison.'),indent=2)+'\n')
PY
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=0 TRACE_SLOTS=16 TRACE_LOCK_OWNER=restrip24-forest-camera
export RE4DC_CONSOLE_EXE='C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe'
export PYTHONDONTWRITEBYTECODE=1 RE4DC_GD_PROFILE='' RE4DC_GD_JITTER='' RE4DC_GD_SEED=''
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:RE4DC_CONSOLE_EXE:PYTHONDONTWRITEBYTECODE:RE4DC_GD_PROFILE:RE4DC_GD_JITTER:RE4DC_GD_SEED"
"$P" -c 'import os;assert os.environ["RE4DC_EMU"]=="console" and os.environ["FP_NOLIMIT"]=="0";print("CAMERA_WINDOWS_CONSOLE_ENV_VERIFIED")'
bash "$HOST/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$HOST/census-bound-run.py")" "$(wslpath -w "$OWN/forest-freeze800-capture.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" 100 --base "$(wslpath -w "$E/base")" --cap "$(wslpath -w "$E/capture-r1")" --syms "$(cat "$O/syms.txt")" --warp "$(wslpath -w "$E/forest-camera-fixture.txt")" --seconds 50 --period 1 --stop 'warp: frozen at tick 800' --grace 2 --name restrip24-forest-camera
echo FOREST_CAMERA_CAPTURE_FINISHED_JUDGEMENT_PENDING
