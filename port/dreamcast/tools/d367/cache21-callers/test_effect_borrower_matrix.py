#!/usr/bin/env python3
"""Source-only controller deletion/activation matrix and archive borrower map."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[4]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    floor=18*1024**3+128*1024**2;start=shutil.disk_usage('/mnt/c').free;assert start>=floor;a.out.mkdir(parents=True,exist_ok=False)
    paths=('src/game/est.cpp','src/game/espgen.cpp','src/game/espgen00.cpp','src/game/espgen10.cpp','src/game/sce_com.cpp','src/game/event.cpp','src/game/read.cpp','src/game/game.cpp','port/dreamcast/game/platform/native_effect.cpp','port/dreamcast/game/platform/include/native_effect_source.h')
    source={};pins={}
    for path in paths:
        data=(REPO/path).read_bytes();source[path]=data.decode();pins[path]=sha(data);out=a.out/'source'/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    selected=[]
    def function(signature):
        text=source['src/game/espgen.cpp'];match=re.search(r'^'+re.escape(signature)+r'[^;\n]*\n\{',text,re.M);assert match
        begin=match.start();end=begin+re.search(r'^}',text[begin:],re.M).end();result=text[begin:end];selected.append(dict(path='src/game/espgen.cpp',signature=signature,line=text.count('\n',0,begin)+1,sha256=sha(result.encode())));return result
    methods=[function(name)for name in('static inline int EspgenIsActive(','void PushEspgen(','void EspgenDeleteEvent(')]
    (a.out/'borrower_actual_methods.inc').write_text('\n'.join(methods)+'\n')
    command=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-I'+str(a.out),str(HERE/'effect_borrower_matrix_host.cpp'),'-o',str(a.out/'test')]
    assert shutil.disk_usage('/mnt/c').free>=floor
    result=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20);(a.out/'compile.txt').write_text(result.stdout);assert result.returncode==0,result.stdout
    result=subprocess.run([str(a.out/'test')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10);(a.out/'run.txt').write_text(result.stdout);assert result.returncode==0,result.stdout;print(result.stdout,end='')
    total=sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file());assert total<=20*1024**2
    receipt=dict(scope='Actual EspgenIsActive/PushEspgen/EspgenDeleteEvent source controls. Archive/reference storage and scheduler source map only; no execution of EstSet/update, native decoder, source SceEventStart or whole reset.',head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),source_sha256=pins,selected_methods=selected,test_sha256={p.name:sha(p.read_bytes())for p in(Path(__file__),HERE/'effect_borrower_matrix_host.cpp')},command=command,output=result.stdout,boundaries=['EspgenWork/Global project only fields used by these three bodies. retained_head is an observational marker; EstSet assignment is source-reviewed separately.','GetEspgenIdMax returns0, so actual Push sets deletion flag without optional destruct dispatch. Real scheduler clears/deferred destructor/app callbacks remain outside this unit.','Eight source Core_flg values, four pool flags and event OFF/ON give64 controls. Surviving active flags establish source policy, not route occurrence or a new lifetime implementation.'],resource_guard=dict(start_C_free_bytes=start,finish_C_free_bytes=shutil.disk_usage('/mnt/c').free,floor_bytes=floor,output_bytes_before_receipt=total,output_limit_bytes=20*1024**2))
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
