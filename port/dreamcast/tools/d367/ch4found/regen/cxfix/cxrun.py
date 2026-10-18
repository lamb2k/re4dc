#!/usr/bin/env python3
"""Replay of Codex cx_room_fixtures.prepare_room (10-13) up to the texture step, per room and le_mirror variant.
usage: c4r-cxrun.py <variant v0|c3|b47> <outroot> <room>...
Writes <outroot>/<room>/<dirname>/{source,mirror,tex}, dirname = 'ancillary' for v0 else 'ancillary-<le_mirror sha12>'."""
import hashlib, subprocess, sys
from pathlib import Path

v = sys.argv[1]
OUT = Path(sys.argv[2])
L = Path('/root/probe/lanes-20261018/ch4regen')
TREE = L / ('cxtree-' + v)
TOOLS = TREE / 'port/dreamcast/tools'
sys.path[:0] = [str(TOOLS / 'd367'), str(TOOLS)]
from assetpipe.rooms import GcIso
import stage_route

iso = GcIso(stage_route.DEFAULT_ISO)
lm = hashlib.sha256((TOOLS / 'le_mirror.py').read_bytes()).hexdigest()[:12]
dirname = 'ancillary' if v == 'v0' else 'ancillary-' + lm


def command(args, log):
    with log.open('w') as f:
        p = subprocess.run([str(x) for x in args], stdout=f, stderr=subprocess.STDOUT)
    return p.returncode


for room in sys.argv[3:]:
    st = 'st' + room[1]
    out = OUT / room / dirname
    src = out / 'source' / st / (room + '.das')
    src.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        src.write_bytes(iso.read(st + '/' + room + '.das'))
    tex = out / 'tex'
    manifest = out / 'textures.manifest'
    manifest.write_text(st + '/' + room + '.arc\n')
    r1 = command([sys.executable, TOOLS / 'le_mirror.py', src.parents[1], out / 'mirror', '--native-rooms'], out / 'mirror.log')
    r2 = 0
    if not (tex / 'native-ui-report.json').exists():
        r2 = command([sys.executable, TOOLS / 'prepare_native_ui.py', src.parents[1], manifest, tex], out / 'textures.log')
    print(room, dirname, 'mirror', r1, 'tex', r2, len(list(tex.glob('*.re4tex'))), flush=True)
