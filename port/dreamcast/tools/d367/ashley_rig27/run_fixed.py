#!/usr/bin/env python3
"""Windows: bounded fp_run on a fixed-high-density base, with fixture equality.

run_fixed.py [fp_run arguments, including --base, --cap, --warp and --syms]
Every launch pins the required cache-model binary and Windows environment.
An absolute57-second subprocess deadline bounds a stalled save/close as well as
the emulation loop. Only this call's recorded child PID may be terminated.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EXPECTED='8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a'
EXE=Path(r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe')
HERE=Path(__file__).resolve().parent


def preflight(args):
    def arg(name):return args[args.index(name)+1] if name in args else None
    base=Path(arg('--base'));cap=Path(arg('--cap'))
    metadata=json.loads((base/'base.json').read_text())
    if metadata.get('fixture_transport')!='fixed-high-density-v1':raise ValueError('Unverified high-density fixture base')
    if '--w11' in args:raise ValueError('This base carries the original empty w11 fixture')
    for name in ('warp','pad'):
        path=arg('--'+name)
        data=Path(path).read_bytes().replace(b'\r',b'') if path else b''
        fixed=metadata['fixed_fixtures'][name]
        if len(data)!=fixed['bytes'] or hashlib.sha256(data).hexdigest()!=fixed['sha256']:
            raise ValueError(f'{name} differs from the actual fixed track3 fixture')
        if fixed['location']!='track03.iso' or fixed['lba']<45000 or fixed['padded_bytes']!=8192:
            raise ValueError('Invalid fixed high-density extent')
        with (base/'track03.iso').open('rb') as track:
            track.seek((fixed['lba']-45000)*2048)
            if track.read(8192)!=data+bytes(8192-len(data)):
                raise ValueError(f'Actual track3 {name} bytes changed')
    if not 30<=int(arg('--seconds') or 40)<=45:raise ValueError('Use30..45 seconds; close/save must fit the60-second limit')
    if hashlib.sha256(EXE.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Wrong cache-model emulator binary')
    if cap.exists():raise ValueError('Use a fresh capture directory')
    return cap


def main():
    args=sys.argv[1:];cap=preflight(args)
    env=dict(os.environ,RE4DC_EMU='console',RE4DC_CONSOLE_DYNAREC='no',RE4DC_GD_PROFILE='gdemu',RE4DC_MAX_FLYCASTS='16')
    assert all(env[k]==v for k,v in (('RE4DC_EMU','console'),('RE4DC_CONSOLE_DYNAREC','no'),('RE4DC_GD_PROFILE','gdemu')))
    command=[sys.executable,str(HERE.parent/'fullplay/fp_run.py')]+args
    child=subprocess.Popen(command,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        rc=child.wait(timeout=57)
    except subprocess.TimeoutExpired:
        # The cap was created by this exact fresh invocation; use its exact PID.
        pidfile=cap/'flycast.pid'
        if pidfile.exists():
            pid=int(pidfile.read_text().strip())
            subprocess.run(['taskkill','/PID',str(pid),'/F'],capture_output=True)
        child.kill();child.wait(timeout=2)
        (cap/'absolute-deadline.json').write_text(json.dumps(dict(status='FAILED',reason='57-second absolute bound',python_pid=child.pid)))
        raise SystemExit('Absolute bound reached; this capture is not an accepted gate')
    if rc:raise SystemExit(rc)
    result=json.loads((cap/'run-result.json').read_text())
    assert result['status']=='RUN_COMPLETE' and not result['errors'],result
    assert result['emu']=='console',result
    assert result['emu_env'].get('RE4DC_CONSOLE_DYNAREC')=='no',result
    assert result['emu_env'].get('RE4DC_GD_PROFILE')=='gdemu',result
    assert hashlib.sha256((cap/'flycast.exe').read_bytes()).hexdigest()==EXPECTED
    assert result['elapsed_s']<=60 and result['emulator_exited'],result
    print('VERIFIED CACHE-MODEL FLYCAST',cap)


if __name__=='__main__':main()
