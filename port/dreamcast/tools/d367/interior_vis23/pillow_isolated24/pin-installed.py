from pathlib import Path
import hashlib,json
R=Path(r'C:\Game Dev\Emulators\codex-lanes\gc-motion24\pillow-isolated-prep-v1')
P=Path(r'C:\Users\lambd\AppData\Local\Programs\Python\Python312\Lib\site-packages\PIL')
def pin(p):return {'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
files={}
for p in sorted(P.rglob('*')):
 if '__pycache__' in p.parts:continue
 assert not p.is_symlink()
 if p.is_file():files[p.relative_to(P).as_posix()]=pin(p)
assert '__init__.py' in files and 'Image.py' in files
inputs={'python':Path(r'C:\Users\lambd\AppData\Local\Programs\Python\Python312\python.exe'),'bound':Path(r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23\census-bound-run.py'),'harness':Path(r'\\wsl.localhost\Ubuntu-24.04\dev\shm\gc-motion24-qa-memory-v2-dbqczoc8\off\source\port\dreamcast\tools\d367\fullplay\fp_run.py'),'capture_template':Path(r'C:\Flycast-Evidence\re4-dreamcast\d367-harness-par\capture_ui_vram.py')}
m={'schema':1,'package_root':str(P),'package_files':files,'package_cache_excluded':True,'inputs':{k:{'path':str(p),**pin(p)} for k,p in inputs.items()},'distribution':{}}
D=P.parent/'pillow-12.3.0.dist-info'
for p in sorted(D.rglob('*')):
 assert not p.is_symlink()
 if p.is_file():m['distribution'][p.relative_to(D).as_posix()]=pin(p)
m['distribution_root']=str(D)
raw=(json.dumps(m,indent=2)+'\n').encode();(R/'PILLOW-PINS.json').write_bytes(raw)
print(len(files),sum(x['size'] for x in files.values()),hashlib.sha256(raw).hexdigest())
