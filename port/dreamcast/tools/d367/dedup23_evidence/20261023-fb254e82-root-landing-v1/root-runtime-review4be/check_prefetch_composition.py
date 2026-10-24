import hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
T=Path('/root/work/lanes/dedup-offline23-current-d5c');H=T/'port/dreamcast/tools/d367/dedup_offline23'
O=Path(tempfile.mkdtemp(prefix='dedup-root-review4be-',dir='/dev/shm'))
spec=importlib.util.spec_from_file_location('composition',H/'check_composition.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source,values,fill=m.generate(T);raw=(T/'port/dreamcast/game/platform/native_static.cpp').read_text()
a=raw.index('// SCENERY_EMIT_PREFETCH_MEMBERS_BEGIN');a=raw.index('\n',a)+1;b=raw.index('// SCENERY_EMIT_PREFETCH_MEMBERS_END',a)
source=source.replace(values['EMIT_PICK'],raw[a:b]+'\n'+values['EMIT_PICK'])
old='__attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){'
assert source.count(old)==1
source=source.replace(old,'__attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n,const Pick* following=nullptr){')
cpp=O/'composition-prefetch.cpp';cpp.write_text(source)
for name,text in {'dc/pvr.h':'#pragma once\n','kos/fs.h':'#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n','dc/matrix.h':'#pragma once\nusing matrix_t=float[4][4];\nstatic void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}\nstatic void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}\n'}.items():
 p=O/'shim'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
env=dict(os.environ,TMPDIR='/dev/shm',PYTHONDONTWRITEBYTECODE='1');runs={}
for decoded in (0,1):
 binary=O/('decoded'+str(decoded));cmd=['g++','-std=c++20','-O2','-ffp-contract=off','-DRE4DC_SCENERY_SELECT_ONLY=1','-DRE4DC_SCENERY_SUBMIT_BATCH=0','-DRE4DC_SCENERY_REPLAY_LEAN=0',f'-DCOMPOSITION_DECODED={decoded}','-DCHECK_DIAGNOSTICS=0','-DRE4DC_SCENERY_SELECT_LEAN2=0','-DRE4DC_SCENERY_EMIT_PREFETCH=1','-I'+str(O/'shim'),'-I'+str(T/'port/dreamcast/game/platform/include'),str(cpp),'-o',str(binary)]
 c=subprocess.run(cmd,capture_output=True,env=env);(O/(str(decoded)+'.compile.log')).write_bytes(c.stdout+c.stderr)
 if c.returncode:raise ValueError(c.stderr.decode()[-6000:])
 for case in (100,101,102,103):
  c=subprocess.run([str(binary),str(case)],capture_output=True,env=env);(O/(str(decoded)+'-'+str(case)+'.stdout')).write_bytes(c.stdout);(O/(str(decoded)+'-'+str(case)+'.stderr')).write_bytes(c.stderr)
  runs[str(decoded)+'-'+str(case)]=dict(rc=c.returncode,stdout_sha256=hashlib.sha256(c.stdout).hexdigest())
comparisons={str(case):runs['0-'+str(case)]==runs['1-'+str(case)] for case in (100,101,102,103)}
r=dict(source='4be08e0110592510e3630c01fa9f49b3ac2fed3d',temporary=str(O),actual_prefetch_functions_sha256=hashlib.sha256(raw[a:b].encode()).hexdigest(),generated_cpp_sha256=hashlib.sha256(source.encode()).hexdigest(),runs=runs,encoded_equals_decoded=comparisons,
 scope='Independent adaptation of existing exact-source host composition: enabled actual prefetch members/signature; same two SH4 FMAC host edges. Not target/guest/performance evidence.')
p=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/root-review4be/PREFETCH-CONTROL.json');p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
