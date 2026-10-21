from pathlib import Path
import argparse,hashlib,json,subprocess,shutil
T=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--ref',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();assert shutil.disk_usage('/mnt/c').free>=18*1024**3+128*1024**2;a.out.mkdir()
s=subprocess.check_output(['git','-C',str(a.source),'show',a.ref+':src/game/eff_sys.cpp'],text=True)
def function(sig):
 b=s.index(sig+'\n{');i=s.index('{',b)+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[b:i]
structs=s[s.index('struct EffIdTbl {'):s.index('extern "C" {')];(a.out/'actual_structs.inc').write_text(structs)
sigs=['GXTexObj* EspPullTexObj(u32 num)','int EspDataLoad(u32 addr, u32 owner, int flag)','int EspDataRelease(u32 owner, int flag, int warn)','int espTexRegist(TEXPalette* tpl, EspAnmData* anm, u8 id, u32 owner)','int estRegist(void* data, void* list, u32 owner)','int sstRegist(void* data, void* list, u32 owner)','int pathRegist(void* data, void* list, u32 owner)','int efmRegist(void* model, void* tpl, void* mot, void* x, u8 id, u32 owner)','int espTexRelease(u32 owner)','int estRelease(u32 owner)','int sstRelease(u32 owner)','int pathRelease(u32 owner)','int efmRelease(u32 owner)','int cEspSystem::GetTexObjFlag(u32 no)','void cEspSystem::SetTexObjFlag(u32 no, int flag)']
methods='\n\n'.join(function(x)for x in sigs);(a.out/'actual_methods.inc').write_text(methods);runs=[]
for mode in [0,1]:
 exe=a.out/('probe'+str(mode));cmd=['g++','-std=c++17','-O1','-g','-fno-pie','-no-pie','-fsanitize=undefined','-fno-sanitize-recover=all','-Wno-int-to-pointer-cast','-DRE4DC_EFFECT_ADMISSION_GUARD='+str(mode),'-I'+str(a.out),str(T/'registration_probe.cpp'),'-o',str(exe)];r=subprocess.run(cmd,capture_output=True,text=True);(a.out/('compile'+str(mode)+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr;r=subprocess.run([str(exe)],capture_output=True,text=True);(a.out/('run'+str(mode)+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr;runs.append({'mode':mode,'command':cmd,'output':r.stdout})
receipt={'scope':'Actual fifteen source function bodies against projected service structs/mocks; no gameplay capacity reachability certified.','ref':a.ref,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'methods_sha256':hashlib.sha256(methods.encode()).hexdigest(),'functions':sigs,'runs':runs,'services':'TEX descriptor lookup/relocation and GX initialize calls are stubs; actual global ID/owner/bitmap/load/release code executes. u32 source pointers preserved through non-PIE static buffers.','output_bytes':sum(p.stat().st_size for p in a.out.iterdir()if p.is_file())};(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'runs':runs,'output_bytes':receipt['output_bytes']},indent=2))
