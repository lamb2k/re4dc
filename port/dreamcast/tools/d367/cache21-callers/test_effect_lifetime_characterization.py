#!/usr/bin/env python3
"""Read-only actual-source effect archive lifetime characterization."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--admission-pair',action='store_true');p.add_argument('--effect-source-revision');p.add_argument('--equivalent-effect-revision',action='append',default=[]);a=p.parse_args()
    floor=18*1024**3+128*1024**2;start=shutil.disk_usage('/mnt/c').free
    assert start>=floor,'Fresh C: source-test admission refused';a.out.mkdir(parents=True,exist_ok=False)
    paths=('src/game/eff_sys.cpp','src/game/emdata.cpp','src/game/event.cpp','src/game/dvd.cpp','include/espgen.h','include/esp.h','src/game/read.cpp')
    source={};pins={};selected=[]
    for path in paths:
        data=(subprocess.check_output(['git','-C',str(REPO),'show',a.effect_source_revision+':'+path])if a.effect_source_revision and path=='src/game/eff_sys.cpp'else(REPO/path).read_bytes());source[path]=data.decode();pins[path]=sha(data)
        out=a.out/'source'/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    def block(path,signature,struct=False):
        text=source[path];begin=text.index(signature);end=begin+re.search(r'^};'if struct else r'^}',text[begin:],re.M).end()
        result=text[begin:end];selected.append(dict(path=path,signature=signature,line=text.count('\n',0,begin)+1,sha256=sha(result.encode())));return result
    types=[block('src/game/eff_sys.cpp','struct '+name+' {',True)for name in('EffIdTbl','EffOfsTbl','EffEfmEnt','EffData')]
    types +=[block('include/espgen.h','struct '+name+' {',True)for name in('SstList','SstData','SstTbl')]
    # Declarations precede definitions; choose function signatures at column0
    # followed by an opening brace, never the extern prototype.
    def function(path,signature):
        text=source[path];match=re.search(r'^'+re.escape(signature)+r'[^;\n]*\n\{',text,re.M);assert match,signature
        begin=match.start();end=begin+re.search(r'^}',text[begin:],re.M).end();result=text[begin:end]
        selected.append(dict(path=path,signature=signature,line=text.count('\n',0,begin)+1,sha256=sha(result.encode())));return result
    methods=[function('src/game/eff_sys.cpp',name)for name in('int EspDataLoad(','int EspDataRelease(','int estRegist(','EspSeqData* EspGetEstAddr(','int estRelease(')]
    methods[0]=methods[0].replace('int EspDataLoad(','int actual_EspDataLoad(',1)
    swaps=[function('src/game/emdata.cpp',name)for name in('int GetEmEffId(','void EspEmDataSwapPush(','void EspEmDataSwapPop(')]
    memory=function('src/game/dvd.cpp','void MemorySwap(')
    for name,text in(('effect_types.inc','\n'.join(types)),('effect_actual_methods.inc','\n'.join(methods)),('effect_actual_swap_methods.inc','\n'.join(swaps)),('effect_actual_memoryswap.inc',memory)):(a.out/name).write_text(text+'\n')
    equivalents={}
    for revision in a.equivalent_effect_revision:
        data=subprocess.check_output(['git','-C',str(REPO),'show',revision+':src/game/eff_sys.cpp']);assert sha(data)==pins['src/game/eff_sys.cpp'];equivalents[revision]=sha(data)
    variants=[]
    for enabled in((0,1)if a.admission_pair else(0,)):
        out=a.out/f'version{enabled}';out.mkdir()
        cmd=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie','-Wall','-Wextra','-fpermissive','-DRE4DC_GAME=1',f'-DRE4DC_EFFECT_ADMISSION_GUARD={enabled}','-I'+str(a.out),str(HERE/'effect_lifetime_characterization_host.cpp'),'-o',str(out/'test')]
        assert shutil.disk_usage('/mnt/c').free>=floor
        compiled=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30);(out/'compile.txt').write_text(compiled.stdout);assert compiled.returncode==0,compiled.stdout
        run=subprocess.run([str(out/'test')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10);(out/'run.txt').write_text(run.stdout);assert run.returncode==0,run.stdout;print(run.stdout.splitlines()[-1])
        variants.append(dict(effect_admission_guard=enabled,command=cmd,output=run.stdout))
    size=sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file());assert size<=20*1024**2
    receipt=dict(scope='Existing EFFECT_ADMISSION_GUARD OFF/ON actual registration/release/est lookup and Push/Pop, plus actual non-CABIN MemorySwap with controlled software ARAM. Not complete CABIN forward/publication/teardown acceptance.',head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),effect_source_revision=a.effect_source_revision,equivalent_complete_effect_sources=equivalents,source_sha256=pins,selected_methods=selected,test_sha256={p.name:sha(p.read_bytes())for p in(Path(__file__),HERE/'effect_lifetime_characterization_host.cpp')},variants=variants,abi_adapters=['cEspSystem projects ownerCnt and estTbl only; actual Sst types extracted. ReadModule pArc lookup/GetDataExt are controlled boundaries.','Actual EspDataLoad definition renamed actual_EspDataLoad; Pop pointer/int bridge calls it and counts invocations.'],boundaries=['Synthetic valid EFF headers/est record markers; texture and effect-model count0 paths. sst/path registration and four non-est release helpers are controlled dispatch boundaries.','Actual estRegist/estRelease/EspGetEstAddr execute; software DMA copies execute actual MemorySwap body with CABIN_SOURCE and EVENT_SWAP_RELOAD undefined, file-range false, null DVD queue and no-op flush.','No private assets or actual live effect/model scheduler. Direct source callability/reproduction, not proved gameplay occurrence or global transaction closure.','bf250 forward/native protocol acceptance remains a separate sealed fixture; this unit does not assert a combined effect-ownership receipt. Invalid shared input compatibility and valid repeated flag1 count mutation are explicit unchanged controls.'],resource_guard=dict(start_C_free_bytes=start,finish_C_free_bytes=shutil.disk_usage('/mnt/c').free,floor_bytes=floor,output_bytes_before_receipt=size,output_limit_bytes=20*1024**2))
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
