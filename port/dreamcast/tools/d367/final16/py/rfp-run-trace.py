"""rfp-run-one.py: one first-pass Flycast scenario, the way Codex's cx-root-batch.py run_one() did it.

Windows Python (Git Bash: `python rfp-run-one.py ...`). Stages in WSL with the private harness copy
(stage-scenario[-v2].py), captures with its run-emulator-novsync.py, gates with Codex's cx_firstpass_check.py
(+ texchk.py), adds the LEON-GC gate (mcheck/leongc_check.py) and the AICA "does not fit" count, then removes only
this scenario's two disc links (sha256 kept). No builds, no traces.

  python rfp-run-one.py --harness "C:\\Game Dev\\Emulators\\re4-rfp-<date>-<label>" --room r117 --view walk \
      --fixture /root/probe/rfp-<date>/fixtures/r117/cx-r117-walk.armed.json --tree /root/probe/rfp-<date>/game \
      [--seconds 60] [--period 15] [--suffix 01] [--stager stage-scenario-v2.py]

Exit 0 = gate PASS, 1 = FAIL, 2 = UNPROVEN, 3 = staging/capture/disk problem (nothing judged).
"""
import argparse, hashlib, json, re, shutil, subprocess, sys, time
from pathlib import Path

DISTRO = 'Ubuntu-24.04'
OVERLAY = '/mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads'
CHECK = '/root/probe/codex-ps2-assets-20261013/tree/port/dreamcast/tools/d367/texchk/cx_firstpass_check.py'
HIDDEN = {'creationflags': subprocess.CREATE_NO_WINDOW}


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def wsl(args, log):
    with open(log, 'x') as out:
        return subprocess.run(['wsl.exe', '-d', DISTRO, '-u', 'root', '--exec'] + args,
                              stdout=out, stderr=subprocess.STDOUT, **HIDDEN).returncode


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--harness', type=Path, required=True)
    p.add_argument('--room', required=True)
    p.add_argument('--view', required=True)
    p.add_argument('--fixture', required=True, help='WSL path of the armed fixture')
    p.add_argument('--tree', required=True, help='WSL path of the game worktree (for mcheck/leongc_check.py)')
    p.add_argument('--seconds', type=int)
    p.add_argument('--period', type=int, default=15)
    p.add_argument('--suffix', default='01')
    p.add_argument('--stager', default='stage-scenario-v2.py')
    p.add_argument('--checker', default=CHECK)
    p.add_argument('--min-free-gb', type=float, default=25.0)
    a = p.parse_args()
    if not re.fullmatch(r'r[0-9a-f]{3}', a.room) or not re.fullmatch(r'[a-z0-9-]+', a.view + a.suffix):
        p.error('room rXXX, view/suffix lowercase')
    root = a.harness.resolve()
    if root.drive.lower() != 'c:':
        p.error('the private harness must be on C: (stage-scenario.py checks /mnt/c capacity)')
    lroot = '/mnt/c/' + root.as_posix()[3:]
    prov = json.loads((root / 'cx-harness-provenance.json').read_text())
    # lane final16 copy for the STRICT trace arm (f3rT): the harness must be a LOGIC_TRACE=1 GAME_DECISION_TRACE=1 one
    assert prov['resolved_diagnostics']['LOGIC_TRACE'] == '1' and prov['resolved_diagnostics']['GAME_DECISION_TRACE'] == '1'
    name = 'cx-%s-%s-%s' % (a.room, a.view, a.suffix)
    sc = root / 'scenarios' / name
    if sc.exists():
        p.error('scenario names are single-use: ' + str(sc))
    seconds = a.seconds or (60 if a.view.startswith('walk') else 45)
    result = dict(scenario=name, room=a.room, view=a.view, fixture=a.fixture, arm=prov['arm'], seconds=seconds)
    free = shutil.disk_usage('C:\\').free
    if free < a.min_free_gb * 1024 ** 3:
        result.update(status='DEFERRED_DISK_SPACE', free_c=free)
        print(json.dumps(result)); return 3
    print(json.dumps(dict(event='STAGING', scenario=name)), flush=True)
    rc = wsl(['python3', lroot + '/' + a.stager, name, '--arm', prov['arm'], '--programs', lroot + '/programs-route.json',
              '--overlay', OVERLAY, '--fixture', a.fixture, '--capture-reserve-mib', '512'],
             root / ('cx-stage-%s.log' % name))
    if rc:
        result.update(status='STAGING_FAILED', returncode=rc, log=str(root / ('cx-stage-%s.log' % name)))
        print(json.dumps(result)); return 3
    meta = json.loads((sc / 'stage.json').read_text())
    assert meta['status'] == 'STAGED_PAYLOAD_IDENTITY_PASS'
    result.update(disc_sha256=meta['disc_sha256'], elf_sha256=meta['elf_sha256'])
    (sc / 'disc.sha256').write_text(meta['disc_sha256'] + '  disc/disc.bin\n')
    (sc / 'PURPOSE.txt').write_text('First pass %s %s (re4-room-firstpass skill): source entry, PS2 world, TEX_CHECK=2, '
                                    'census=1, MCHECK_LEONGC=1, LOGIC_TRACE=0 GAME_DECISION_TRACE=0. Fixture %s.\n'
                                    % (a.room, a.view, a.fixture))
    began = time.time()
    with open(root / ('cx-run-%s.log' % name), 'x') as out:
        cap = subprocess.run([sys.executable, str(root / 'run-emulator-novsync.py'), name, '--seconds', str(seconds),
                              '--period', str(a.period)], stdout=out, stderr=subprocess.STDOUT)
    rr = sc / 'capture' / 'run-result.json'
    result['capture_returncode'] = cap.returncode
    if not rr.exists():
        result['status'] = 'CAPTURE_RESULT_MISSING'
        print(json.dumps(result)); return 3
    run = json.loads(rr.read_text())
    result['capture'] = {k: run.get(k) for k in ('status', 'elapsed_s', 'errors', 'owned_emulator_exited')}
    log = 'capture/run-output.txt'
    wsl(['python3', '-B', a.checker, lroot + '/scenarios/%s/%s' % (name, log), '--room', a.room,
         '--output', lroot + '/scenarios/%s/cx-firstpass-check.json' % name], root / ('cx-check-%s.log' % name))
    gate = sc / 'cx-firstpass-check.json'
    if gate.exists():
        g = json.loads(gate.read_text())
        result['checks'] = {k: v['status'] for k, v in g.items() if isinstance(v, dict) and 'status' in v}
        result['overall'] = g['overall']
        result['memory_observations'] = g.get('memory_observations', [])
    lg = wsl(['python3', a.tree + '/port/dreamcast/tools/d367/mcheck/leongc_check.py', lroot + '/scenarios/%s/%s' % (name, log)],
             sc / 'leongc-check.txt')
    result['checks'] = dict(result.get('checks', {}),
                            leon_gc={0: 'PASS', 1: 'FAIL'}.get(lg, 'UNPROVEN'))
    text = (sc / log).read_bytes().decode('latin1')
    result['aica_does_not_fit'] = [l for l in text.splitlines() if 'does not fit' in l][:8]
    result['stills'] = [str(s) for s in sorted((sc / 'capture' / 'shots').glob('*/frames/fb0.png'))]
    if run.get('owned_emulator_exited'):
        for rel in ('disc/disc.bin', 'capture/disc.bin'):
            d = sc / rel
            if d.exists():
                assert sha(d) == meta['disc_sha256'], d
                (d.parent / 'disc.sha256').write_text(meta['disc_sha256'] + '  disc.bin\n')
                d.unlink()
        result['discs_removed'] = True
    else:
        result['discs_removed'] = False  # an emulator we own is still alive: stop that PID only, then delete by hand
    result['elapsed_seconds'] = round(time.time() - began, 1)
    statuses = list(result.get('checks', {}).values())
    result['status'] = 'COMPLETE_AWAITING_REVIEW'
    (sc / 'rfp-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if 'overall' not in result:
        return 3
    return 1 if 'FAIL' in statuses else 2 if 'UNPROVEN' in statuses else 0


if __name__ == '__main__':
    sys.exit(main())
