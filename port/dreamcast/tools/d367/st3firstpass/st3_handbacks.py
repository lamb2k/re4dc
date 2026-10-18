"""Stage-3 adaptation of Codex's asset-audit/stream_handbacks.py (copied as stream_handbacks_codex.orig.py).
Changes: one lane (this one), Disc-2 GC pin instead of Disc 1, single pass (no polling), writes
st3-handback-state.json in this lane, and does NOT append to CODEX-COORDINATION.md. Same verification:
manifest fingerprint rooms, verify_overlay runtime inventory, PS2/GC source pins, package hashes == hand-back."""
from pathlib import Path
import sys, json, time, tempfile
ROOT = Path('/root/probe/lanes-20261014/st3')
sys.path.insert(0, str(ROOT / 'tools/port/dreamcast/tools'))
import build_ps2_assets as build
STATE = ROOT / 'st3-handback-state.json'
PROFILE = json.loads(build.PROFILE.read_text())
GC2_SHA = PROFILE['gc_source_disc2']['sha256']
status = json.loads((ROOT / 'evidence/status.json').read_text())
state = {}
with tempfile.TemporaryDirectory(prefix='st3-handoff-check-') as scratch:
    checker = build.runtime_checker(Path(scratch))
    for room, row in status.items():
        if row['status'] != 'ready':
            print('SKIP', room, row['status']); continue
        report = Path(row['handback']); d = json.loads(report.read_text())
        out = Path(d['out']).resolve()
        assert out.is_relative_to(ROOT / 'tools/.assets')
        m = json.loads((out / 'manifest.json').read_text())
        assert m['fingerprint']['rooms'] == [room]
        checked = build.verify_overlay(out, [room], checker)
        assert m['runtime_files'] == checked, 'runtime inventory changed'
        assert m['sources']['ps2']['sha256'] == 'eb0874cf29dc48c994fd183e52a3b186b47b0a341281a0c2db24a1f18757cb66'
        assert m['sources']['gc']['sha256'] == GC2_SHA
        runtime = out / 'rooms' / room
        packages = {n: build.record(runtime / n) for n in ['ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids']}
        assert packages == d['packages'], 'handback package hash mismatch'
        v = m['rooms'][room]['validation']
        state[room] = {'handback': str(report), 'manifest': str(out / 'manifest.json'), 'packages': packages,
                       'validation': v, 'elapsed_seconds': d['elapsed_seconds'], 'reported_unix': time.time()}
        print('HANDED_BACK', room, v['heap_bytes'], v['texture_vram_bytes'], v['textures'], flush=True)
STATE.write_text(json.dumps(state, indent=2) + '\n')
print('rooms', len(state))
