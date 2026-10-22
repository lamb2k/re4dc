from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
src=L/'owned-window-recovered-j-r201-postboss-full-gallery-escape-still.py';assert hashlib.sha256(src.read_bytes()).hexdigest()=='03a4970c567ad0c0e2ceb74b151304086a3b84fb628b5b97f7f3dab8c97b3295';s=src.read_text()
old="   if rr<3500:close.append(dict(source=e['source_list_no'],distance=rr,target_direction_dot=toward,escape_away=toward<0))"
new="   if rr<3500:\n    t=max(0,min(1,toward/max(1,dx*dx+dz*dz)));clearance=math.hypot(ex-t*dx,ez-t*dz);close.append(dict(source=e['source_list_no'],distance=rr,target_direction_dot=toward,escape_away=toward<0,straight_target_path_minimum_xz=clearance))"
assert s.count(old)==1;s=s.replace(old,new,1)
old="  if any(e['distance']<1200 or not e['escape_away']for e in close):"
new="  if any(e['distance']<700 or e['straight_target_path_minimum_xz']<900 or (distance<6000 and not e['escape_away'])for e in close):"
assert s.count(old)==1;s=s.replace(old,new,1)
s=s.replace('original_live_wave_within3500_on_approach_or1200_any_direction_stop','original_full_spacing_retreat_path_clearance900_or_distance700_stop',1)
s=s.replace("'scope':'Recovered J finite full gallery escape:","'scope':'Recovered J full combat-spacing retreat, normal controls only: target at least6000away may pass laterally only with read-only straight-path clearance>=900 from every close live actor; distance<700 stops unconditionally, later nearby approach stops. Any actual injury/phase/death/PID/collision/resource guards retained. No game writes or health modifications. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-wave-spacing-retreat-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
