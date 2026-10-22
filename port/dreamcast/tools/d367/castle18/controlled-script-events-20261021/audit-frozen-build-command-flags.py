from pathlib import Path
import hashlib,json,re,shutil
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';T=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18');O=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\lanes\route\out-c21jmW');HC=T/'port/dreamcast/tools/d367/castle18/controlled-script-events-20261021'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
log=O/'build.log';rows=[]
for n,line in enumerate(log.read_text(encoding='utf-8').splitlines(),1):
 if ' -c ' not in line:continue
 if not any(x in line for x in ['dbgwarp_bridge.cpp','/r201.cpp','/r208.cpp','/r204.cpp','vmu_save.cpp','modules.cpp','/message.cpp']):continue
 defines={k:v or '1' for k,v in re.findall(r'-D([A-Za-z_][A-Za-z_0-9]*)(?:=([^\s]+))?',line)}
 rows.append(dict(line=n,command_sha256=hashlib.sha256(line.encode()).hexdigest(),command=line,explicit_RE4DC_definitions={k:v for k,v in defines.items()if k.startswith('RE4DC_')}))
assert any('dbgwarp_bridge.cpp'in r['command'] for r in rows)
assert all(any('/'+r+'.cpp'in x['command']for x in rows)for r in ['r201','r208','r204'])
result=dict(build_log_sha256=sha(log),resolved_flags_sha256=sha(R/'builds/c21jmW/resolved-knobs.txt'),rows=rows,scope='Retained actual compiler command evidence for selected event/warp/loader TUs. Missing explicit macro tokens are not default-zero evidence; resolved make flags remain separately recorded. Historical full object/preprocess dependency closure not reconstructed.')
p=D/'frozen-master-selected-compile-commands.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');shutil.copyfile(p,HC/p.name);shutil.copyfile(L/'audit-frozen-build-command-flags.py',HC/'audit-frozen-build-command-flags.py')
print(json.dumps(dict(report_sha256=sha(p),rows=len(rows),retained_build_log_sha256=sha(log))))
