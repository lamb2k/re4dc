from pathlib import Path
import hashlib
L=Path(__file__).parent
src=(L/'observe-controlled-r204-event006.py').read_text().replace("cap==D/'route-walk-controlled-event006'","cap==D/'route-walk-controlled-event007'")
old="fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));assert fb,'Framebuffer not ready';p=cap/'shots'/('controlled-'+label);p.mkdir(parents=True,exist_ok=False)"
new="""fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));fb_source='current native log'
 if not fb:
  # FrozenELF pvr_get_front/back disassembly: _pvr_state8c483e00, two framebuffer structs312/320.
  # StandardDC conversion proven against closed005 native log and closed006 state; exact inherited buffers required.
  pair=(u32(0x8c483e00+312),u32(0x8c483e00+320));assert pair==(u32(0x8c483e00+312),u32(0x8c483e00+320)), 'Unstable framebuffer pair'
  assert pair==(0x230980,0x630980),'Inherited framebuffer identity changed'
  ptrs=[((0xd2800000+(v&0x7fffff))*2)&0xffffffff for v in pair]
  for ptr in ptrs:fc.framebuffer_offset(ptr)
  fb=['fb=%x,%x'%tuple(ptrs)];fb_source='current live frozenELF pvr_state+312/320, checked inherited005/006 buffers';events.append(dict(framebuffer_readonly_fallback=dict(source=fb_source,native=[hex(v)for v in pair],rgb565=[hex(v)for v in ptrs])))
 p=cap/'shots'/('controlled-'+label);p.mkdir(parents=True,exist_ok=False)"""
assert old in src;src=src.replace(old,new).replace("source_frame_interval=[before,after],observation=row","source_frame_interval=[before,after],framebuffer_source=fb_source,observation=row")
src=src.replace("if not movie_shot and rsf is not None and rsf&0x80000000 and age()<35:","if not movie_shot and rsf is not None and rsf&0x80000000 and 2<age()<35:")
src=src.replace('CONTROLLED direct continuation of closed005 movie state.','CONTROLLED direct continuation of closed006 movie state.').replace('Original005 chapter6','Original005 chapter6')
compile(src,'observe007','exec');(L/'observe-controlled-r204-event007.py').write_text(src)
src=(L/'run-controlled-event006.py').read_text().replace("cap=D/'route-walk-controlled-event006'","cap=D/'route-walk-controlled-event007'").replace("observer=L/'observe-controlled-r204-event006.py'","observer=L/'observe-controlled-r204-event007.py'").replace("seed=D/'route-walk-controlled-event005/data'","seed=D/'route-walk-controlled-event006/data'").replace('40556645e59094f21b3051eecbffb0c71d08182acdef60e321ac76eb33705f86','606f9193c58c5e9d5df4b5374a3b4d4e864914f25b8da6ee09c4fd842dd672ff').replace('closed controlled005 movie snapshot','closed controlled006 movie snapshot').replace('Continue005 in-progress','Continue006 in-progress').replace('movie-continuation006','movie-continuation007').replace("print('Controlledevent005 closed;","print('Controlledevent007 closed;")
compile(src,'run007','exec');(L/'run-controlled-event007.py').write_text(src)
src=(L/'run-controlled-event006.sh').read_text().replace('event006','event007');(L/'run-controlled-event007.sh').write_bytes(src.replace('\r','').encode())
for n in ['observe-controlled-r204-event007.py','run-controlled-event007.py']:print(n,hashlib.sha256((L/n).read_bytes()).hexdigest())
