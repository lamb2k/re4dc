from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='1b8ed650c9eb3c908bac6fa1ef1066713c1482c73cea2922e40013bc194fd510';s=p.read_text()
s=s.replace("{'forward','dash'}","{'forward'}").replace("{'forward','dash','left'if delta>0 else'right'}","{'forward','left'if delta>0 else'right'}")
s=s.replace("samples[-1]['source_Key_on']=hex(key_on)","samples[-1]['source_Key_on']=hex(key_on);samples[-1]['source_footstep_flag']=bool(u32(pg+0x5010)&0x80000000)",1)
s=s.replace("'scope':'Actual J123 original injury528/90 state;","'scope':'Full normal walking flank after original bait shot; ordinary Forward and source-ack Back/B quickturn, no running outside quickturn. Source footstep flag recorded; no silent-walking claim assumed. Latest health and actual injury/PID/collision/resource guards retained. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-full-walk-flank-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
