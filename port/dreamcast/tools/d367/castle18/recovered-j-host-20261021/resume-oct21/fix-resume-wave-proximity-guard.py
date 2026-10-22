from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
old=L/'owned-window-recovered-j-r201-postboss-wave-walk-still.py';assert hashlib.sha256(old.read_bytes()).hexdigest()=='3e32c81df79db2bde8a2c3b58a24b452988948c9c2eb4c8b50f87f5db9a11761'
s=old.read_text();bad=" and e['id']!='0x1b'";assert s.count(bad)==1
# Source-em-set family id0x1b includes both boss type10 and Ganado type7.
# All live actors must count; dead Garrador is excluded by hp>0 already.
s=s.replace(bad,'',1)
dst=L/'owned-window-recovered-j-r201-postboss-wave-live-guard-walk-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True)
print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
