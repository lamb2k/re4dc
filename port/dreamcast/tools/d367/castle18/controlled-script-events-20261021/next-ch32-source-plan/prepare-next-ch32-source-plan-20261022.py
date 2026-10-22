from pathlib import Path
import json,hashlib,re,datetime,struct
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');T=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18');TREE=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\castle21-recovered-j-content-20261021\tree');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((L/'NEXT-CH32-SOURCE-CAPABILITY-20261022.json').read_text());actual={}
for n,x in a['selected_manifest_assets'].items():
 p=TREE/n;assert p.is_file(),n;assert p.stat().st_size==x['size'],n;v=sha(p);assert v==x['sha256'],n;actual[n]=dict(size=p.stat().st_size,sha256=v,actual_extracted_tree_verified=True)
log=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\lanes\route\out-c21jmW\build.log');selected=[]
for i,line in enumerate(log.read_text(errors='replace').splitlines(),1):
 if any(('/src/st2/r'+r+'.o')in line and ('src/st2/r'+r+'.cpp')in line for r in ['204','205','209','20a','20b']):
  selected.append(dict(line=i,sha256=hashlib.sha256(line.encode()).hexdigest(),source=re.findall(r'src/st2/r[0-9a-f]+\.cpp',line),defines=[v for v in re.findall(r'-D[A-Z0-9_]+(?:=[^ ]+)?',line)if any(s in v for s in ['ALIVE_CAP','ROUTE_MOVIE','PS2_ENEMY'])]))
x=dict(scope='Read-only exact extracted asset verification and retained compile command sites; no guest/build. Existing ccd160 binding closes ELF/raw/image/18-overlay identities; this is not a whole historical dependency-closure rebuild.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parent_receipt_sha256=sha(L/'NEXT-CH32-SOURCE-CAPABILITY-20261022.json'),actual_assets=actual,retained_buildlog_sha256=sha(log),compile_sites=selected,source_current_vs_frozen='git diff12a on r204/r205/r209/r20a/r20b/r206 and game/dbgwarp_bridge.cpp empty before plan; source hashes in parent receipt',master_overlays={k:v for k,v in json.loads((D/'master/base-manifest.json').read_text()).items()if k in ['dc/st2_1.ovl','dc/em2d.ovl','dc/em22.ovl']})
p=L/'NEXT-CH32-ACTUAL-ASSET-COMPILE-20261022.json';assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');print('sidecar',sha(p),p.stat().st_size,'actual assets',len(actual),'compile sites',len(selected))
fixture='''squeeze 49152 0
name castle21-CONTROLLED-ch32-drain014
room 0x205
jp 0
chapter 7
pos 46118.5419921875 996.8269653320312 48787.291015625
ang 0
alivelog 30
dump
'''
p=L/'controlled-ch32-drain014-warp-DRAFT.txt';assert not p.exists();p.write_bytes(fixture.encode());print('draftfixture',sha(p))
