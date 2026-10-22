from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
src=L/'owned-window-recovered-j-r201-postboss-wave-live-guard-walk-still.py';assert hashlib.sha256(src.read_bytes()).hexdigest()=='cda3c566ebc5cfc76413996a929fb311975a8277bcb5677704be25e0f7fc6273';s=src.read_text()
old="  if near<3500:transition(set());events.append({'original_live_wave_enemy_within3500_stop_before_approach':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break"
assert s.count(old)==1
new='''  close=[]
  for e in samples[-1]['wave_status']['active_character_actors']:
   if e['hp']<=0:continue
   ex,ez=e['pos'][0]-pos[0],e['pos'][2]-pos[2];rr=math.hypot(ex,ez);toward=ex*dx+ez*dz
   if rr<3500:close.append(dict(source=e['source_list_no'],distance=rr,target_direction_dot=toward,escape_away=toward<0))
  samples[-1]['close_enemy_target_escape_geometry']=close
  if any(e['distance']<1200 or not e['escape_away']for e in close):transition(set());events.append({'original_live_wave_within3500_on_approach_or1200_any_direction_stop':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break'''
s=s.replace(old,new,1)
start=s.index('  if (distance<tolerance or arrived_frame is not None)and target_i==len(targets)-1:');end=s.index('  if distance<tolerance:\n',start)
s=s[:start]+'''  if distance<tolerance and target_i==len(targets)-1:
   transition(set());events.append({'normal_full_original_gallery_escape_complete':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
'''+s[end:]
s=s.replace("'scope':'Recovered J current sealed postboss Follow walk:","'scope':'Recovered J finite full gallery escape: allow normal retreat away from every nearby actor, retain3500 approach stop and1200 unconditional stop; no terminal wait after fullroute. Latest health and original death/door/lever gates remain. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-postboss-full-gallery-escape-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
