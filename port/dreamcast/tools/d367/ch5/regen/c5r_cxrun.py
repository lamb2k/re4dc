#!/usr/bin/env python3
"""ch5regen: replay of the st3 lane's cx_room_fixtures prepare_room texture step (10-14) for island rooms,
using ch4regen's rebuilt Codex tool tree (read-only). Source = GC review disc 2 gcm (as recorded: --iso re4_review_disc2.gcm).
usage: c5r_cxrun.py <tree> <outroot> <room>...  -> <outroot>/<room>/ancillary-<le_mirror sha12>/{source,mirror,tex}"""
import hashlib, subprocess, sys
from pathlib import Path

TREE = Path(sys.argv[1]); OUT = Path(sys.argv[2])
TOOLS = TREE / 'port/dreamcast/tools'
sys.path[:0] = [str(TOOLS / 'd367'), str(TOOLS)]
from assetpipe.rooms import GcIso
ISO = '/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm'
iso = GcIso(ISO)
lm = hashlib.sha256((TOOLS / 'le_mirror.py').read_bytes()).hexdigest()[:12]
dirname = 'ancillary-' + lm

def command(args, log):
    with log.open('w') as f:
        return subprocess.run([str(x) for x in args], stdout=f, stderr=subprocess.STDOUT, cwd='/tmp').returncode

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
    r2 = command([sys.executable, TOOLS / 'prepare_native_ui.py', src.parents[1], manifest, tex], out / 'textures.log')
    print(room, dirname, 'mirror', r1, 'tex', r2, len(list(tex.glob('*.re4tex'))), flush=True)
