"""Exact-child guard for the explicitly new bounded-53/55 console profile.

Windows CLI only. Host tests exercise ChildGuard with ordinary host processes.
A guard PASS is process evidence, never game/runtime acceptance.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import threading
import time

PROFILE = 'RR_QUICK_QA_CONSOLE_OBSERVE53_CHILD55_V1'
OBSERVE_SECONDS = 53
CHILD_SECONDS = 55.0
GIB = 1024 ** 3
CONSOLE_SHA = '8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a'
BASE_CFG_SHA = 'e92b5817e28d4e96f4e7d038d64b365e356264d025e55b03f8184a0dd1817840'
HARNESS_SHA = '646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747'
TEMPLATE_HELPERS = {
    'read_log.py': '6c43705318caa4c63fddd2995c04bdc9c3730abfe66400192be89f4d1e845059',
    'capture_ui_vram.py': '14a3561e730df57e29d271e6fb7cdbf44b8fea2d1b7b2be076a5cb4590856d57',
}
HEAD = 'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'


def load_json(path):
    def unique(rows):
        out = {}
        for k, v in rows:
            require(k not in out, 'duplicate JSON key: ' + k)
            out[k] = v
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def require(ok, why):
    if not ok:
        raise ValueError(why)


def verify_files(pins):
    require(isinstance(pins, dict) and pins, 'missing actual file pins')
    for path, digest in pins.items():
        require(len(digest) == 64 and sha(path) == digest, 'file pin mismatch: ' + path)


class ChildGuard:
    """Uses only the exact Popen object; never process-name/global termination."""
    def __init__(self, cap, console_sha, free_bytes, deadline=CHILD_SECONDS,
                 floor=20 * GIB, popen=None):
        self.cap = Path(cap).resolve()
        self.console_sha = console_sha
        self.free_bytes = free_bytes
        self.deadline = deadline
        self.floor = floor
        self.popen = popen or subprocess.Popen
        self.child = None
        self.started = None
        self.ended = None
        self.reason = None
        self.cfg_sha = None
        self.command = None
        self.stop = threading.Event()
        self.watch = None
        self.cap_identity = None
        self.owned_tracks = {}
        self.removed_tracks = []

    def launch(self, args, *a, **kw):
        # Harness spawns reader/capture helpers too. Only exact guest basename is
        # intercepted; source-pinned harness has one such call, tested separately.
        if isinstance(args, (list, tuple)) and args and Path(args[0]).name.lower() == 'flycast.exe':
            require(self.child is None, 'second guest refused')
            exe = Path(args[0]).resolve()
            require(exe == self.cap / 'flycast.exe', 'foreign guest path')
            require(Path(kw.get('cwd', '')).resolve() == self.cap, 'foreign guest cwd')
            require(list(map(str, args[1:])) == ['disc.gdi'], 'unexpected guest arguments')
            require(sha(exe) == self.console_sha, 'guest is not pinned console bytes')
            require(self.free_bytes() >= self.floor, 'C below absolute floor')
            cfg_bytes = (self.cap / 'emu.cfg').read_bytes()
            with open(self.cap / 'bounded-launch-emu.cfg', 'xb') as f:
                f.write(cfg_bytes)
            self.cfg_sha = hashlib.sha256(cfg_bytes).hexdigest()
            st = self.cap.stat()
            self.cap_identity = [st.st_dev, st.st_ino]
            for name in ('track01.bin', 'track01.iso', 'track02.raw', 'track03.bin', 'track03.iso'):
                path = self.cap / name
                if path.exists():
                    require(not path.is_symlink(), 'unexpected track symlink')
                    member = path.stat()
                    self.owned_tracks[name] = [member.st_dev, member.st_ino, member.st_size]
            with open(self.cap / 'owned-capture-tracks.json', 'x', encoding='utf-8') as f:
                json.dump(dict(capture_identity=self.cap_identity, tracks=self.owned_tracks,
                               scope='NEW_CAPTURE_ONLY_NO_SOURCE_MEDIA_RETIREMENT'), f, indent=2)
            self.command = list(map(str, args))
            self.started = time.monotonic()
            self.child = self.popen(args, *a, **kw)
            self.watch = threading.Thread(target=self._watch, daemon=True)
            self.watch.start()
            return self.child
        return self.popen(args, *a, **kw)

    def unlink_track(self, path, original, *a, **kw):
        path = Path(path)
        require(path.parent.resolve() == self.cap and path.name in self.owned_tracks, 'foreign unlink refused')
        st = self.cap.stat()
        member = path.lstat()
        require([st.st_dev, st.st_ino] == self.cap_identity, 'capture directory changed')
        require(not path.is_symlink() and [member.st_dev, member.st_ino, member.st_size] == self.owned_tracks[path.name], 'capture track changed')
        result = original(path, *a, **kw)
        self.removed_tracks.append(path.name)
        return result

    def _watch(self):
        while not self.stop.wait(0.01):
            if self.child.poll() is not None:
                self.ended = time.monotonic()
                return
            if time.monotonic() - self.started >= self.deadline:
                self.reason = 'CHILD_DEADLINE'
            else:
                try:
                    if self.free_bytes() < self.floor:
                        self.reason = 'C_ABSOLUTE_FLOOR'
                except Exception:
                    self.reason = 'FLOOR_MONITOR_FAILED'
            if self.reason:
                self.child.terminate()
                return

    def finish(self):
        if self.child is not None:
            if self.child.poll() is None:
                self.reason = self.reason or 'HARNESS_LEFT_CHILD'
                self.child.terminate()
                try:
                    self.child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait(timeout=2)
            self.ended = self.ended or time.monotonic()
        self.stop.set()
        if self.watch:
            self.watch.join(timeout=3)
        elapsed = None if self.started is None else self.ended - self.started
        if elapsed is not None and elapsed > self.deadline:
            self.reason = self.reason or 'CHILD_ELAPSED_OVER_BOUND'
        if self.child is None:
            self.reason = 'NO_GUEST'
        return dict(profile=PROFILE, status='FAIL' if self.reason else 'PROCESS_GUARD_PASS',
                    reason=self.reason, child_limit_s=self.deadline,
                    observed_child_elapsed_upper_s=elapsed, actual_console_sha256=self.console_sha,
                    saved_launch_cfg_sha256=self.cfg_sha, command=self.command,
                    removed_owned_capture_tracks=self.removed_tracks,
                    child_exit_code=None if self.child is None else self.child.poll(),
                    runtime_qualified=False)


def validate_request(cfg, argv):
    require(cfg['profile'] == PROFILE and cfg['source'] == HEAD, 'wrong profile/source')
    require(cfg['status'] == 'ROOT_REVIEWED_CURRENT_HEAD_INPUTS', 'inputs not reviewed')
    require(cfg.get('console_sha256') == CONSOLE_SHA, 'wrong reviewed console')
    require(cfg.get('base_cfg_sha256') == BASE_CFG_SHA, 'wrong template cfg')
    require(argv.count('--cap') == 1 and argv.count('--seconds') == 1, 'explicit unique cap/seconds required')
    sec = int(argv[argv.index('--seconds') + 1])
    require(0 < sec <= OBSERVE_SECONDS, 'outside explicit observation profile')
    cap = argv[argv.index('--cap') + 1]
    require(cap in cfg['expected_runs'] and cfg['expected_runs'][cap] == argv, 'unplanned child invocation')
    require(not Path(cap).exists(), 'capture path already exists')
    require(cfg.get('programme_assets_closure_receipt_sha256') and cfg.get('input_pins'),
            'missing programme/assets closure binding')
    verify_files(cfg['input_pins'])
    require(cfg['input_pins'].get(cfg['closure_receipt']) == cfg['programme_assets_closure_receipt_sha256'],
            'closure receipt not actually pinned')
    require(cfg['input_pins'].get(cfg['console']) == CONSOLE_SHA, 'console pin absent')
    require(cfg['input_pins'].get(cfg['template_cfg']) == BASE_CFG_SHA, 'template cfg pin absent')
    require(cfg['harness_sha256'] == HARNESS_SHA and sha(cfg['harness']) == HARNESS_SHA, 'harness drift')
    require(cfg['input_pins'].get(cfg['harness']) == HARNESS_SHA, 'harness input pin absent')
    require(Path(cfg['template_cfg']).resolve() == Path(r'C:\Flycast-Evidence\re4-dreamcast\d367-harness-par\emu.cfg').resolve(), 'wrong actual harness template path')
    for name, digest in TEMPLATE_HELPERS.items():
        required_path = str(Path(cfg['template_cfg']).parent / name)
        require(cfg['input_pins'].get(required_path) == digest, 'missing/wrong actual template helper pin: ' + name)
    for data in (Path(cfg['template_cfg']).parent / 'data').rglob('*'):
        if data.is_file():
            require(str(data) in cfg['input_pins'], 'unbound template data file: ' + str(data))
    return Path(cap)


def run(cfg, argv):
    require(os.name == 'nt', 'actual harness requires Windows; use host controls on Linux')
    cap = validate_request(cfg, argv)
    require(shutil.disk_usage('C:\\').free >= 24 * GIB, 'C below staging floor')
    requested = cfg.get('_requested_env', {})
    require(all(k.startswith('RE4DC_GD_') or k == 'FP_NOLIMIT' for k in requested), 'unsupported forwarded environment')
    require(cfg['expected_env'].get(argv[argv.index('--cap') + 1]) == requested, 'unplanned environment overrides')
    for k in list(os.environ):
        if k.startswith('RE4DC_GD_') or k in ('FP_NOLIMIT', 'RE4DC_CONSOLE_DYNAREC'):
            del os.environ[k]
    os.environ.update(requested)
    os.environ.update(RE4DC_EMU='console', RE4DC_CONSOLE_EXE=cfg['console'], RE4DC_MAX_FLYCASTS='16')
    old_popen, old_argv, old_unlink = subprocess.Popen, sys.argv, Path.unlink
    guard = ChildGuard(cap, CONSOLE_SHA, lambda: shutil.disk_usage('C:\\').free)
    rc, error = 0, None
    try:
        subprocess.Popen = guard.launch
        Path.unlink = lambda path, *a, **kw: guard.unlink_track(path, old_unlink, *a, **kw)
        sys.argv = [cfg['harness'], *argv]
        runpy.run_path(cfg['harness'], run_name='__main__')
    except SystemExit as ex:
        rc = ex.code if isinstance(ex.code, int) else (1 if ex.code else 0)
    except BaseException as ex:
        rc, error = 1, repr(ex)
    finally:
        subprocess.Popen, sys.argv, Path.unlink = old_popen, old_argv, old_unlink
        receipt = guard.finish()
    receipt.update(source=HEAD, harness_sha256=cfg['harness_sha256'], harness_rc=rc, error=error,
                   input_pins=cfg['input_pins'], argv=argv)
    if rc or error:
        receipt['status'] = 'FAIL'
    require(cap.is_dir(), 'harness failed before capture creation')
    with open(cap / 'bounded-console.json', 'x', encoding='utf-8') as f:
        json.dump(receipt, f, indent=2)
        f.write('\n')
    return 0 if receipt['status'] == 'PROCESS_GUARD_PASS' else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True)
    p.add_argument('--request')
    p.add_argument('argv', nargs=argparse.REMAINDER)
    a = p.parse_args()
    cfg = load_json(a.config)
    if a.request:
        request = json.loads(base64.urlsafe_b64decode(a.request))
        cfg['_requested_env'] = request['env']
        return run(cfg, request['argv'])
    return run(cfg, a.argv[1:] if a.argv[:1] == ['--'] else a.argv)


if __name__ == '__main__':
    sys.exit(main())
