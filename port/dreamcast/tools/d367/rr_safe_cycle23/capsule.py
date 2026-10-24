"""Source-only RR capsule preparation and explicitly admitted observation entry.

Never runs installed rr-cycle. Build/stage remain separate reviewed operations.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from console_guard import HEAD, PROFILE, require, sha, verify_files, load_json

PREFIX = 'port/dreamcast/tools/d367/'
RR_LOCK = Path('/root/rr/rr.lock')
SLOT = Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/stat-guest-slot.sh')
CONSOLE = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/flycast-console-bin/flycast-console.exe')
TEMPLATE = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par')


def put(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'x', encoding='utf-8', newline='\n') as f:
        f.write(body)


def replace_once(text, before, after):
    require(text.count(before) == 1, 'source shape changed: ' + before[:80])
    return text.replace(before, after)


def patch_jobs(s, fpd):
    s = replace_once(s, 'FPD=$WT/fullplay', "FPD='" + fpd + "'")
    s = replace_once(s, '  local n=$1 b=$2 s=$3 sec=$4; shift 4',
                     '  local n=$1 b=$2 s=$3 sec=$4; shift 4\n  [ "$sec" -le 53 ] || sec=53')
    s = replace_once(s, 'if [ "$TIER" = qa ]; then',
                     '[ "$TIER" = quick ] || [ "$TIER" = qa ] || exit 2\nif [ "$TIER" = qa ]; then')
    return s


def patch_kos(s):
    # Keep scenes, all levels, required END checks and the complete summary intact.
    import re
    n = 0
    def sub(m):
        nonlocal n
        n += 1
        return m[1] + '53'
    out = re.sub(r'(\[(?:fight|call|door|leave100|leave103)\]=)(?:60|75)', sub, s)
    require(n == 5, 'expected all five KOS scene durations')
    return out


def patch_gd(s):
    return replace_once(s, 'SECS=${SECS:-60}',
                        'SECS=53 # Explicit bounded profile; caller override cannot extend it.')


def prepare(repo, out):
    require(not out.exists(), 'capsule must be a new exclusive path')
    require(subprocess.check_output(['git', '-C', str(repo), 'rev-parse', HEAD], text=True).strip() == HEAD,
            'source commit unavailable')
    out.mkdir(parents=True)
    pins = {}
    def blob(rel):
        b = subprocess.check_output(['git', '-C', str(repo), 'show', HEAD + ':' + PREFIX + rel])
        pins[HEAD + ':' + PREFIX + rel] = hashlib.sha256(b).hexdigest()
        return b.decode()
    # Freeze installed orchestration read-only for audit. The old cycle/QA builder
    # are kept as .REFERENCE, deliberately never executable through this adapter.
    for name in ('rr-cycle.sh', 'rr-jobs.sh', 'rr-flycast.sh', 'rr-qa-tier.sh', 'rr-qa.sh',
                 'rr-judge.py', 'rr-newest.sh', 'recipe.conf', 'release-checks.conf'):
        p = Path('/root/rr/bin') / name
        body = p.read_text()
        pins[str(p)] = sha(p)
        put(out / 'installed-reference' / (name + '.REFERENCE'), body)
    for name in ('fp_run.py', 'kos_squeeze.sh', 'gdemu_gate.sh'):
        body = blob('fullplay/' + name)
        if name == 'fp_run.py':
            put(out / 'fullplay' / '_fp_run_original.py', body)
        else:
            put(out / 'fullplay' / name, patch_kos(body) if name.startswith('kos') else patch_gd(body))
    # Exact tracked fixture bytes; no disc/media/package copying.
    rows = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-r', '--name-only', HEAD,
                                   PREFIX + 'fullplay/segments'], text=True).splitlines()
    for rel in rows:
        data = subprocess.check_output(['git', '-C', str(repo), 'show', HEAD + ':' + rel])
        p = out / 'fullplay' / 'segments' / Path(rel).name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        pins[HEAD + ':' + rel] = hashlib.sha256(data).hexdigest()
    trace = blob('trace_lock.sh')
    put(out / 'trace_lock.sh', trace)
    put(out / 'stat-guest-slot.sh', SLOT.read_text())
    pins[str(SLOT)] = sha(SLOT)
    here = Path(__file__).resolve().parent
    for name in ('capsule.py', 'console_guard.py'):
        put(out / name, (here / name).read_text())
    # Windows Python wrapper is the sole fp_run path in the private FPD. Both
    # stock nested shells resolve dirname($0)/fp_run.py and therefore reach it.
    linux = str(out.resolve())
    fpd = '//wsl.localhost/Ubuntu-24.04' + linux + '/fullplay'
    wrapper = '''import base64,json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
cfg=os.environ.get('RR_SAFE_CONFIG'); lease=os.environ.get('RR_SAFE_LEASE')
if not cfg or not lease: raise SystemExit('missing live root RR lease/config')
env={k:v for k,v in os.environ.items() if k.startswith('RE4DC_GD_') or k == 'FP_NOLIMIT'}
payload=base64.urlsafe_b64encode(json.dumps(dict(argv=sys.argv[1:],env=env)).encode()).decode()
cmd=['wsl.exe','-d','Ubuntu-24.04','-u','root','--','python3',ROOT+'/capsule.py','child',cfg,lease,payload]
raise SystemExit(subprocess.call(cmd))
'''.replace('ROOT+', repr(linux) + '+')
    put(out / 'fullplay' / 'fp_run.py', wrapper)
    installed_jobs = Path('/root/rr/bin/rr-jobs.sh').read_text()
    put(out / 'bin' / 'rr-jobs.sh', patch_jobs(installed_jobs, fpd))
    fly = Path('/root/rr/bin/rr-flycast.sh').read_text()
    fly = replace_once(fly, 'EV=${1:?evidence}; MAX=${2:-12}', 'EV=${1:?evidence}; MAX=3')
    fly = replace_once(fly, 'export RE4DC_MAX_FLYCASTS=${RE4DC_MAX_FLYCASTS:-12}',
                       'export RE4DC_MAX_FLYCASTS=16')
    put(out / 'bin' / 'rr-flycast.sh', fly)
    # Judges remain byte identical. Do not execute their global REPORT writer;
    # root must prepare reviewed private-report successor before whole-cycle use.
    pins[str(CONSOLE)] = sha(CONSOLE)
    for name in ('emu.cfg', 'read_log.py', 'capture_ui_vram.py'):
        pins[str(TEMPLATE / name)] = sha(TEMPLATE / name)
    files = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    manifest = dict(profile=PROFILE, source=HEAD, status='SOURCE_CAPSULE_NOT_EXECUTION_ADMITTED',
                    source_pins=pins, files=files, automatic_cycle_enabled=False,
                    runtime_qualified=False)
    put(out / 'CAPSULE.json', json.dumps(manifest, indent=2) + '\n')
    return manifest


def start_ticks(pid):
    return Path('/proc/%s/stat' % pid).read_text().rpartition(') ')[2].split()[19]


def live_lease(path, config):
    d = load_json(path)
    require(d['config_sha256'] == sha(config), 'configuration changed during lease')
    require(start_ticks(d['pid']) == d['start_ticks'], 'stale root RR lease')
    st = os.stat('/proc/%s/fd/%s' % (d['pid'], d['fd']))
    now = RR_LOCK.stat()
    require([st.st_dev, st.st_ino] == d['lock_identity'] == [now.st_dev, now.st_ino], 'wrong lock inode')
    # A live open fd is not proof of flock: /proc/locks must show the exact
    # holder PID and canonical lock inode. Never accept caller RR_LOCKED=1.
    key = '%02x:%02x:%d' % (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino)
    require(any('FLOCK' in r and r.split()[4:6] == [str(d['pid']), key]
                for r in Path('/proc/locks').read_text().splitlines()), 'root does not hold canonical RR lock')
    return d


def verify_capsule(cfg):
    root = Path(__file__).resolve().parent
    manifest_path = root / 'CAPSULE.json'
    windows_root = '//wsl.localhost/Ubuntu-24.04' + str(root)
    for key, rel in [('wrapper_windows', '/fullplay/fp_run.py'), ('guard_windows', '/console_guard.py'),
                     ('harness', '/fullplay/_fp_run_original.py')]:
        require(cfg[key].replace(chr(92), '/') == windows_root + rel, 'foreign capsule executable: ' + key)
    require(sha(manifest_path) == cfg['capsule_manifest_sha256'], 'capsule manifest drift')
    m = load_json(manifest_path)
    require(m['source'] == HEAD and m['profile'] == PROFILE and not m['automatic_cycle_enabled'], 'wrong capsule')
    for rel, digest in m['files'].items():
        require(not Path(rel).is_absolute() and '..' not in Path(rel).parts, 'unsafe capsule member')
        require(sha(root / rel) == digest, 'capsule member drift: ' + rel)
    require({'capsule.py','console_guard.py','fullplay/fp_run.py','fullplay/_fp_run_original.py',
             'fullplay/kos_squeeze.sh','fullplay/gdemu_gate.sh','stat-guest-slot.sh','trace_lock.sh',
             'bin/rr-jobs.sh','bin/rr-flycast.sh'} <= m['files'].keys(), 'incomplete capsule')
    return m


def audit(cfg):
    # Does not replace or weaken any semantic RR judge. Success here proves
    # only that every *planned* invocation has a complete bounded receipt.
    require(set(cfg['expected_runs']) == set(cfg['capture_paths_wsl']), 'capture map incomplete')
    require(bool(cfg['expected_runs']), 'no expected invocations')
    for cap, argv in cfg['expected_runs'].items():
        directory = Path(cfg['capture_paths_wsl'][cap])
        r = load_json(directory / 'bounded-console.json')
        require(r['status'] == 'PROCESS_GUARD_PASS' and r['harness_rc'] == 0 and not r['error'], 'child failed')
        require(r['argv'] == argv and r['input_pins'] == cfg['input_pins'], 'invocation/closure mismatch')
        require(r['source'] == HEAD and r['profile'] == PROFILE and r['runtime_qualified'] is False, 'receipt scope mismatch')
        require(r['harness_sha256'] == cfg['harness_sha256'] and r['actual_console_sha256'] == cfg['console_sha256'], 'binary/source mismatch')
        require(r['child_limit_s'] == 55 and 0 <= r['observed_child_elapsed_upper_s'] <= 55, 'actual child over bound')
        require(sha(directory/'bounded-launch-emu.cfg') == r['saved_launch_cfg_sha256'], 'saved configuration mismatch')
        require((directory/'run-result.json').is_file() and (directory/'run-output.txt').is_file(), 'reader results missing')
        actual = load_json(directory/'run-result.json')
        require(actual['emu'] == 'console' and actual['seconds'] == int(argv[argv.index('--seconds')+1]), 'actual reader profile mismatch')
        require(actual['status'] == 'RUN_COMPLETE' and not actual.get('errors'), 'reader did not complete')
    return dict(status='PLANNED_PROCESS_BOUNDS_COMPLETE', count=len(cfg['expected_runs']),
                runtime_qualified=False, semantic_judges_required=True)


def child(config, lease, payload):
    cfg = load_json(config)
    live_lease(lease, config)
    verify_capsule(cfg)
    root = Path(__file__).resolve().parent
    env = dict(os.environ, TRACE_SLOTS='16', TRACE_LOCK_OWNER='rr-safe-console53',
               RE4DC_MAX_FLYCASTS='16')
    # Windows Python must be explicitly bound by root's input pins too.
    require(cfg['windows_python'] in cfg['input_pins'], 'unbound Windows Python')
    verify_files({cfg['windows_python_wsl']: cfg['input_pins'][cfg['windows_python']]})
    command = ['bash', str(root / 'stat-guest-slot.sh'), 'bash', str(root / 'trace_lock.sh'),
               sys.executable, str(root / 'capsule.py'), 'launch', config, lease, payload]
    return subprocess.call(command, env=env)


def launch(config, lease, payload):
    cfg = load_json(config)
    live_lease(lease, config)
    verify_capsule(cfg)
    return subprocess.call([cfg['windows_python_wsl'], cfg['guard_windows'], '--config',
                            cfg['config_windows'], '--request', payload])


def hold(config, command):
    import fcntl
    cfg = load_json(config)
    require(cfg['profile'] == PROFILE and cfg['source'] == HEAD, 'wrong source/profile')
    require(cfg['status'] == 'ROOT_REVIEWED_CURRENT_HEAD_INPUTS', 'execution not admitted')
    require(cfg['admission']['release_priority_granted'] is True, 'release priority missing')
    require(cfg['admission']['phase'] == 'FINAL_GDI_BOOT_ONLY', 'whole-cycle entry is not implemented/admitted')
    require(len(cfg['expected_runs']) == 1, 'boot-first phase permits exactly one planned child')
    argv = next(iter(cfg['expected_runs'].values()))
    require('--disc' in argv and '--base' not in argv and '--warp' not in argv and '--pad' not in argv, 'first phase must use actual final GDI without fixtures')
    require(argv[argv.index('--seconds') + 1] == '45', 'retain original boot45 observation')
    require('--stop' in argv and argv[argv.index('--stop') + 1] == 'state title=', 'retain original boot title judge trigger')
    require('--grace' in argv and argv[argv.index('--grace') + 1] == '5', 'retain original boot grace5')
    expected_command = [cfg['windows_python_wsl'], cfg['wrapper_windows'], *argv]
    require(command == expected_command, 'only private reader command is permitted')
    require(command == cfg['admission']['command'], 'unreviewed command')
    # Config/admission is caller assertion, not runtime qualification. All source
    # and closure pins are still verified by actual guard before each child.
    verify_capsule(cfg)
    require(cfg['config_windows'].replace(chr(92), '/') == '//wsl.localhost/Ubuntu-24.04' + str(Path(config).resolve()), 'foreign config alias')
    free = os.statvfs('/mnt/c').f_bavail * os.statvfs('/mnt/c').f_frsize
    reserve = int(cfg['admission']['maximum_new_c_bytes'])
    require(reserve >= 1024**3 and free >= max(24 * 1024**3, 20 * 1024**3 + reserve), 'peak/C floor admission fails')
    with RR_LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lease = Path(cfg['lease_path'])
        st = os.fstat(lock.fileno())
        put(lease, json.dumps(dict(pid=os.getpid(), fd=lock.fileno(), start_ticks=start_ticks(os.getpid()),
                                  lock_identity=[st.st_dev, st.st_ino], config_sha256=sha(config))))
        env = dict(os.environ, RR_SAFE_CONFIG=str(Path(config).resolve()), RR_SAFE_LEASE=str(lease.resolve()),
                   MSYS2_ENV_CONV_EXCL='RR_SAFE_CONFIG;RR_SAFE_LEASE',
                   WSLENV='RR_SAFE_CONFIG:RR_SAFE_LEASE:MSYS2_ENV_CONV_EXCL')
        # Git Bash inherits these Linux config/lease names for the WSL child
        # route. No installed rr-cycle invocation, metadata promotion or cleanup.
        return subprocess.call(command, env=env)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    x = sub.add_parser('prepare'); x.add_argument('repo', type=Path); x.add_argument('out', type=Path)
    x = sub.add_parser('hold'); x.add_argument('config'); x.add_argument('command', nargs=argparse.REMAINDER)
    x = sub.add_parser('audit'); x.add_argument('config')
    for name in ('child', 'launch'):
        x = sub.add_parser(name); x.add_argument('config'); x.add_argument('lease'); x.add_argument('payload')
    a = p.parse_args()
    if a.action == 'prepare':
        d = prepare(a.repo, a.out); print(json.dumps({k: d[k] for k in ('status', 'profile', 'source')})); return 0
    if a.action == 'audit': print(json.dumps(audit(load_json(a.config)), indent=2)); return 0
    if a.action == 'hold': return hold(a.config, a.command[1:] if a.command[:1] == ['--'] else a.command)
    return (child if a.action == 'child' else launch)(a.config, a.lease, a.payload)


if __name__ == '__main__':
    sys.exit(main())
