from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-original-bell120-still.py'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='316ed982467860997ee4a6776f6dbe9afce23bd22cf03b62d7f22cf3263262de';s=src.read_text();old='if health[0]<1200 or health[2]<90:';assert s.count(old)==1
s=s.replace(old,"if health[0]<_sp['health'][0] or health[2]<_sp['health'][2]:",1)
dst=L/'owned-window-recovered-j-r201-original-bell-current-health-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
