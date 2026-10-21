from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='1b8ed650c9eb3c908bac6fa1ef1066713c1482c73cea2922e40013bc194fd510';s=p.read_text()
s=s.replace('input_refreshes=0\n while','input_refreshes=0;cycle_wait=False;cycle_stable=None\n while',1)
at=s.index('  now=time.monotonic();stagnation.append(')
block='''  if target_i==1 and (distance<tolerance or cycle_wait):
   transition(set());cycle_wait=True;gg=samples[-1]['Garrador'];sep=math.hypot(pos[0]-gg['pos'][0],pos[2]-gg['pos'][2]);ff=u32(pg+0x51e4)
   if gg['player_back_dot']>=-600 and sep<6500:events.append({'original_cycle_close_frontal_stop':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   stable_upper=gg['pos'][1]>1700 and gg['pos'][2]>-40000 and gg['routines'][0]==1 and gg['routines'][1]==16 and sep>7500
   if stable_upper:
    if cycle_stable is None:cycle_stable=ff
    if ff-cycle_stable>=30:
     events.append({'original_upper_patrol16_and_far_separation_stable30ticks_before_full_west_return':dict(samples[-1])});assert len(targets)==3;target_i=2;target=targets[2];stagnation=[];cycle_wait=False;time.sleep(.03);continue
   else:cycle_stable=None
   time.sleep(.03);continue
'''
s=s[:at]+block+s[at:]
s=s.replace("'scope':'Actual J123 original injury528/90 state;","'scope':'One consolidated original full east escape, neutral observation of original upper patrol16/far separation for30source ticks, then full west firing-line return. Require3targets, no shortcut during active charge/damage pose. Current exact health and all injury/phase/PID/collision/resource guards remain; no game writes. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-combined-escape-patrol-return-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
