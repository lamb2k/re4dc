from pathlib import Path
import ctypes,json,math,sys,time
from ctypes import wintypes as W
import fp_run_qa_sixfix as pad
from qa_owned_checkpoint import capture_checkpoint
cap=Path(sys.argv[1]);deadline=time.monotonic()+58
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4
while time.monotonic()<deadline:
    if (cap/'owned-process.json').exists() and (cap/'readonly-combat-io.jsonl').exists() and (cap/'run-start.json').exists():break
    time.sleep(.1)
else:raise SystemExit('No own observer')
resume=Path(sys.argv[2]);meta=json.loads((cap/'run-start.json').read_text());prior=json.loads((resume/'run-start.json').read_text())
assert Path(meta['seed']).resolve()==(resume/'data').resolve(), 'Only exact supplied predecessor state'
assert meta['elf_sha256']==prior['elf_sha256']=='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053'
assert meta['disc_sha256']==prior['disc_sha256']==json.loads((cap.parent/'sixfix-master/master-receipt.json').read_text())['track03_sha256']
owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000,False,owner['pid']);assert h
path=ctypes.create_unicode_buffer(32768);size=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size))
assert Path(path.value).resolve()==Path(owner['path']).resolve()
c,e,kt,ut=(W.FILETIME() for _ in range(4));assert k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),ctypes.byref(kt),ctypes.byref(ut))
assert (c.dwHighDateTime<<32|c.dwLowDateTime)==owner['start_filetime']
start=time.monotonic();deadline=start+45
steps=[('up','same-current handgun no-op'),('right','shotgun'),('up','handgun return1'),('left','rifle1'),('left','TMP1'),('up','handgun return2'),('right','shotgun return1'),('up','handgun return3'),('left','rifle return1'),('left','TMP return1'),('up','handgun return4'),('right','shotgun return2'),('up','handgun return5')]
with (cap/'normal-weapon-controls.jsonl').open('x') as out:
    def latest():
        row=json.loads((cap/'readonly-combat-io.jsonl').read_text().splitlines()[-1]);assert time.time()-(cap/'readonly-combat-io.jsonl').stat().st_mtime<1.5;return row
    def write(row):out.write(json.dumps(row)+'\n');out.flush()
    def stop_owned(reason):
        request=dict(pid=owner['pid'],start_filetime=owner['start_filetime'],reason=reason);tmp=cap/'owned-stop-request.tmp';tmp.write_text(json.dumps(request)+'\n');tmp.replace(cap/'owned-stop-request.json')
    for index,(direction,label) in enumerate(steps):
        while time.monotonic()<deadline:
            try:s=latest()
            except (IndexError,json.JSONDecodeError,AssertionError):time.sleep(.05);continue
            if 'health' not in s:time.sleep(.05);continue
            if s['health'][0]<1000:stop_owned('WEAPON_CONTROL_HEALTH_GUARD');raise SystemExit()
            if s['phase']==[3,0] and s['stop']=='0x0' and 'player_pos'in s:break
            time.sleep(.05)
        else:stop_owned('WEAPON_CONTROL_WAIT_TIMEOUT');raise SystemExit()
        px,py,pz=s['player_pos'];assert -84000<px<-82000 and 800<py<1000 and -39000<pz<-38000,'Safe original pre-s03 control location'
        if index==0:write(dict(screenshot=capture_checkpoint(cap,'weapon-start','Warm control entry','Same-program seed, safe pre-s03 location')))
        before=s;ft=[W.FILETIME()for _ in range(4)];assert k.GetProcessTimes(h,*[ctypes.byref(x)for x in ft]);assert not(ft[1].dwHighDateTime or ft[1].dwLowDateTime)
        windows=pad.press(owner['pid'],['x',direction],.25);last_reads=None;quiet_since=time.monotonic()
        while time.monotonic()<deadline:
            try:s=latest()
            except (IndexError,json.JSONDecodeError,AssertionError):time.sleep(.05);continue
            if s['disc']['reads']!=last_reads:last_reads=s['disc']['reads'];quiet_since=time.monotonic()
            if s['phase']==[3,0] and s['stop']=='0x0' and s['frame']>=before['frame']+20 and time.monotonic()-quiet_since>=.3 and s['hand']['job_state']==0 and all(w<0 for w in s['hand']['want']):break
            time.sleep(.05)
        else:stop_owned('WEAPON_TRANSITION_TIMEOUT');raise SystemExit()
        write(dict(step=index,label=label,direction=direction,windows=windows,before=before,after=s,disc_delta={k:s['disc'][k]-before['disc'][k]for k in ['reads','bytes','block_us']},hand_delta={k:s['hand'][k]-before['hand'][k]for k in ['reads','read_bytes','misses','async_reads','copies','yields']},texture_delta=s['texture']['loads']-before['texture']['loads']))
        if index in [4,9,12]:write(dict(step=index,screenshot=capture_checkpoint(cap,'weapon-step-%02d'%index,label,'Completed normal transition; counters in adjacent rows')))
    stop_owned('NORMAL_WEAPON_CYCLES_COMPLETE')
