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
resume=Path(sys.argv[2]);current=json.loads((cap/'run-start.json').read_text());prior=json.loads((resume/'run-start.json').read_text());assert Path(current['seed']).resolve()==(resume/'data').resolve();assert current['elf_sha256']==prior['elf_sha256']=='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053';assert current['disc_sha256']==prior['disc_sha256']==json.loads((cap.parent/'sixfix-master/master-receipt.json').read_text())['track03_sha256']
owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000,False,owner['pid']);assert h
path=ctypes.create_unicode_buffer(32768);size=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size))
assert Path(path.value).resolve()==Path(owner['path']).resolve()
c,e,kt,ut=(W.FILETIME() for _ in range(4));assert k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),ctypes.byref(kt),ctypes.byref(ut))
assert (c.dwHighDateTime<<32|c.dwLowDateTime)==owner['start_filetime']
start=time.monotonic();deadline=start+50;last_frame=None;fired=0
stage='area';nav=0;first_actor=None;selected=False;radio_skip=False
seen={};completed=set();points=[(-83300,-38000),(-84200,-35000),(-84950,-32400)]
with (cap/'normal-combat-controller.jsonl').open('x') as out:
    def record(s,**kw):
        row=dict(host_s=round(time.monotonic()-start,3),frame=s['frame'],stage=stage,**kw)
        out.write(json.dumps(row)+'\n');out.flush()
        (cap/'normal-progress.json').write_text(json.dumps(dict(stage=stage,nav=nav,fired=fired,first_actor=first_actor,selected=selected,radio_skip=radio_skip,completed=sorted(completed),last_frame=s['frame']),indent=2)+'\n')
    def action(names,hold,s):
        ft=[W.FILETIME() for _ in range(4)];assert k.GetProcessTimes(h,*[ctypes.byref(x) for x in ft])
        if ft[1].dwHighDateTime or ft[1].dwLowDateTime:raise EOFError()
        n=pad.press(owner['pid'],names,hold);record(s,keys=names,hold=hold,windows=n,weapon=s['weapon'],health=s['health'])
    def face(err,s,tolerance=.20):
        if abs(err)>tolerance:
            action(['turnleft' if err>0 else 'turnright'],min(.65,abs(err)/2.25),s);time.sleep(.07);return False
        return True
    while time.monotonic()<deadline:
        try:
            lines=(cap/'readonly-combat-io.jsonl').read_text().splitlines();s=json.loads(lines[-1])
            if time.time()-(cap/'readonly-combat-io.jsonl').stat().st_mtime>1.5:time.sleep(.05);continue
            log=(cap/'run-output.txt').read_text(errors='replace')
            # Fresh boot only. Movie detection deliberately precedes source-frame equality: movies freeze Frame_cnt.
            for event in ['10003','10020']:
                if ('route movie start: id='+event) in log:
                    seen.setdefault(event,time.monotonic())
                    if event=='10020':
                        if 'route movie terminal=1 id=10020 frames=571/571' in log and event not in completed:completed.add(event);record(s,status='ORIGINAL_S20_NATURAL_EOF')
                        continue
                    if event not in completed and time.monotonic()-seen[event]>=2:
                        record(s,screenshot=capture_checkpoint(cap,'movie-'+event,'Original source event movie','Before ordinary START skip'));action(['start'],.15,s);completed.add(event);time.sleep(.3)
            if s['frame']==last_frame:time.sleep(.05);continue
            last_frame=s['frame']
            if '10020' in completed and not radio_skip and 'SS/eng/ss_term.dat' in log and s.get('ssloop') and s['stop']!='0x0':
                seen.setdefault('radio_ready_wait',time.monotonic())
                if time.monotonic()-seen['radio_ready_wait']<6:time.sleep(.05);continue
                record(s,screenshot=capture_checkpoint(cap,'radio-open','Original post-s20 radio','Original modal before normal START close'));action(['start'],.15,s);radio_skip=True;stage='await_world';time.sleep(.5);continue
            if not all(k in s for k in ['player_pos','player_yaw','health','actors']):time.sleep(.05);continue
            px,py,pz=s['player_pos'];world=-100000<px<-65000 and 0<py<7000 and -45000<pz<-20000
            if '10020' in completed and not radio_skip and 'SS/eng/ss_term.dat' in log and not world and s['stop']!='0x0':
                action(['start'],.15,s);radio_skip=True;stage='await_world';time.sleep(.5);continue
            if s['phase']!=[3,0] or s['health'][0]<=0 or s['stop']!='0x0' or not world:time.sleep(.05);continue
            enemies=[a for a in s['actors'] if a['id']==18 and a['hp']>0 and int(a['be_flag'],16)&4]
            if stage=='area':
                if '10003' in completed:
                    if not selected:action(['x','right'],.25,s);selected=True;stage='first_fight';time.sleep(.7)
                else:
                    assert -85000<px<-81000 and -40000<pz<-33000,'Original areaA approach bounds'
                    action(['fwd'],.5,s)
                continue
            if stage=='first_fight':
                if first_actor is not None:
                    old=[a for a in s['actors'] if a['ptr']==first_actor]
                    if old and old[0]['hp']<=0:stage='await_s20';record(s,status='ORIGINAL_FIRST_KILL',screenshot=capture_checkpoint(cap,'first-kill','Original first Ganado killed','Source death callback; s20 pending'));continue
            if stage in ['await_s20','await_world']:
                if radio_skip:
                    stage='finished';record(s,status='ORIGINAL_RADIO_CLOSED_AFTER_NATURAL_S20',screenshot=capture_checkpoint(cap,'natural-movie-return','Natural s20 EOF and normal radio close','Live original world restored'));request=dict(pid=owner['pid'],start_filetime=owner['start_filetime'],reason='SIXFIX_NATURAL_MOVIE_RETURN_COMPLETE');tmp=cap/'owned-stop-request.tmp';tmp.write_text(json.dumps(request)+'\n');tmp.replace(cap/'owned-stop-request.json');break
                else:time.sleep(.05);continue
            if stage=='walk':
                assert -90000<px<-70000 and 500<py<6000 and -45000<pz<-25000,'Original house navigation bounds'
                if nav<2:
                    dx=points[nav][0]-px;dz=points[nav][1]-pz;dist=math.hypot(dx,dz)
                    if dist<350:nav+=1;continue
                else:
                    if -85200<px<-84700 and -32600<pz<-32000:
                        err=(-math.pi/2-s['player_yaw']+math.pi)%(2*math.pi)-math.pi
                        if face(err,s,.18):action(['a'],.2,s);stage='jump';time.sleep(1)
                        continue
                    dx=points[2][0]-px;dz=points[2][1]-pz;dist=math.hypot(dx,dz)
                err=(math.atan2(dx,dz)-s['player_yaw']+math.pi)%(2*math.pi)-math.pi
                if face(err,s,.28):action(['fwd'],min(.4,dist/1900),s)
                continue
            if stage=='jump':
                if px<-87000:stage='ambush';record(s,status='ORIGINAL_WINDOW_OUTSIDE')
                else:time.sleep(.1)
                continue
            if stage not in ['first_fight','ambush'] or not enemies:time.sleep(.1);continue
            target=min(enemies,key=lambda a:(a['pos'][0]-px)**2+(a['pos'][2]-pz)**2)
            if first_actor is None:first_actor=target['ptr']
            dx=target['pos'][0]-px;dz=target['pos'][2]-pz
            if math.hypot(dx,dz)>6500:time.sleep(.1);continue
            err=(math.atan2(dx,dz)-s['player_yaw']+math.pi)%(2*math.pi)-math.pi
            if not face(err,s,.14):continue
            action(['shoot'],.15,s);fired+=1;time.sleep(.35)
            if fired%5==0:action(['reload'],.15,s);time.sleep(1)
        except EOFError:break
        except (IndexError,json.JSONDecodeError):time.sleep(.05)