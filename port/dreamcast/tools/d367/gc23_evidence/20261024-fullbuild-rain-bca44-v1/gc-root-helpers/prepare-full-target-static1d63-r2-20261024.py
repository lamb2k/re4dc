from pathlib import Path
import hashlib,json
own=Path(r'C:\Game Dev\Emulators\codex-lanes\gc-port23')
old=Path(r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\gc-port23-full-target-scratch')
dest=Path(r'C:\Flycast-Evidence\re4-dreamcast\gc-port23-20261023\full-target-static1d63-attempt1')
dest.mkdir(exist_ok=True)
for source,name in [(old/'receipt.json','receipt.json'),(old/'off/build.log','off-build.log'),(old/'off/command.json','off-command.json'),(own/'full-target-static1d63-20261024.py','full-target-static1d63-20261024.py'),(own/'full-target-static1d63-20261024.sh','full-target-static1d63-20261024.sh')]:
 (dest/name).write_bytes(source.read_bytes())
(dest/'FAILURE.json').write_text(json.dumps(dict(status='MAKE_PREFLIGHT_REFUSAL',reason='Pinned SH4ZAM submodule was uninitialized in this tree; no compiler or linker reached',source='1d63cffe3a232c402418f2f2d919e7abae476957',pinned_submodule='33fa4850cacb30dd0ad35485ef035526ec4ce782',members={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file() and p.name!='FAILURE.json'}),indent=2)+'\n')
s=(own/'full-target-static1d63-20261024.py').read_text().replace('gc-port23-full-target-scratch','gc-port23-full-target2-scratch')
s=s.replace(" scratch=TREE/'port/dreamcast/game/obj'", " module=TREE/'port/dreamcast/game/third_party/sh4zam'\n if subprocess.check_output(['git','-C',str(module),'rev-parse','HEAD'],text=True).strip()!='33fa4850cacb30dd0ad35485ef035526ec4ce782':raise RuntimeError('SH4ZAM source pin mismatch')\n if subprocess.check_output(['git','-C',str(module),'status','--porcelain'],text=True).strip() or not(module/'include/sh4zam/shz_xmtrx.h').is_file():raise RuntimeError('SH4ZAM dirty/missing')\n scratch=TREE/'port/dreamcast/game/obj'")
s=s.replace(" if len(list(PROFILE.glob('*.ovl')))!=14", " pins.update({str(p):sha(p) for p in module.rglob('*') if p.is_file() and p.suffix in ('.h','.hpp','.inc')})\n if len(list(PROFILE.glob('*.ovl')))!=14")
compile(s,'full-target-static1d63-r2-20261024.py','exec')
(own/'full-target-static1d63-r2-20261024.py').write_text(s,newline='\n')
sh=(own/'full-target-static1d63-20261024.sh').read_text().replace('full-target-static1d63-20261024','full-target-static1d63-r2-20261024')
(own/'full-target-static1d63-r2-20261024.sh').write_text(sh,newline='\n')
print('Original refusal preserved; fresh R2 outputs, explicit pinned SH4ZAM preflight. No build yet.')