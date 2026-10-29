#!/usr/bin/env python3
"""Execute the actual Build35 gap-hook source with controlled external edges.

Audit OFF/ON must preserve semantic results and callbacks exactly. Counter
expectations use observed operations and explicit admission/refusal cases.
This does not execute a game route or qualify console cost/geometry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
DEF=DC/'game/platform/include/fallback_audit35.def'


def function(source,signature,start=0):
    """Recovered multiline functions end at column zero, even across #if arms."""
    at=source.index(signature,start)
    while True:
        brace=source.index('{',at)
        if ';' not in source[at:brace]:break
        at=source.index(signature,at+len(signature))
    end=re.search(r'^}',source[brace+1:],re.MULTILINE)
    assert end,signature
    return source[at:brace+1+end.end()]


def fragments(kind):
    if kind=='motion':
        source=DC/'game/platform/native_motion.cpp'
        return {'ACQUIRE':function(source.read_text(),'extern "C" int re4dc_motion_acquire(')},[source]
    if kind=='cloth':
        source=ROOT/'src/game/cloth.cpp';chain=ROOT/'src/game/pendulum.cpp'
        s=source.read_text();p=chain.read_text()
        first=s.index('#if defined(RE4DC_CLOTH_SPRING)',s.index('// One simulation step'))
        last=s.index('// A free cloth work',first)
        prefixes=[]
        for name in ('PenClothMove','PenClothMove2','PenClothMove3'):
            f=function(p,'void '+name+'(')
            prefixes.append(f[:f.index('    floorY = -100000.0f;')]+'    return;\n}')
        return {'SPRINGS':s[first:last],'CHAINS':'\n'.join(prefixes),
                'SKIP':function(p,'void PenClothSkipTick(')},[source,chain]
    if kind=='collision':
        source=ROOT/'src/game/at_mod.cpp';s=source.read_text()
        first=s.index('#if defined(RE4DC_ATCHK) && RE4DC_ATCHK')
        f=function(s,'void EmAtCheck(')
        return {'COLLISION':s[first:s.index(f)+len(f)]},[source]
    if kind=='effects':
        source=ROOT/'src/game/espgen.cpp';delete=ROOT/'src/game/est.cpp';header=ROOT/'include/esp.h'
        s=source.read_text();d=delete.read_text();h=header.read_text()
        def alternatives(text,signature):
            one=function(text,signature);two=function(text,signature,text.index(one)+len(one))
            return '#if RE4DC_FX_SCAN\n'+one+'\n#else\n'+two+'\n#endif'
        first=s.index('#define FX_EG_WORDS');last=s.index('\n#else\n#define FX_EG_STALE',first)
        esp_first=d.index('static inline int fxEspDelHit(');esp_last=d.index('void EspDeleteEvent()',esp_first)
        esp_first=d.rfind('#if defined(RE4DC_FX_SCAN)',0,esp_first)
        return {'ACTIVE':function(s,'static inline int EspgenIsActive('),'EGMAP':s[first:last],
                'MOVEONE':function(s,'static inline void fxEgMoveOne('),'MOVE':function(s,'int EspgenMove('),
                'TRANSONE':function(s,'static inline void fxEgTransOne('),'TRANS':alternatives(s,'int EspgenTrans('),
                'DELHIT':function(s,'static inline int fxEgDelHit('),'DELSKIP':function(s,'static void fxChkEgDelSkip('),
                'DELETE':alternatives(s,'void EspgenDelete('),'PUSH':function(s,'void PushEspgen('),
                'ESPDELETE':d[esp_first:esp_last], 'OWNER':function(d,'static void espOwnRecount('),
                'OWNERHASH':function(h,'static inline unsigned long re4dcEspOwnB(')},[source,delete,header]
    raise ValueError(kind)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true')
    p.add_argument('--only',choices=('motion','collision','effects','cloth'))
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    names=re.findall(r'^FA35_REASON\((\w+),',DEF.read_text(),re.M)
    configs={'motion':[dict(RE4DC_MOTION_INDEX=index,RE4DC_MOTION_LEASE_LEAN=lean) for index in (0,1) for lean in (0,1)],
             'cloth':[dict(RE4DC_CLOTH_SPRING=mode) for mode in (0,1,2)],
             'collision':[dict(zip(('RE4DC_ATCHK','RE4DC_ATCHK_LIST','RE4DC_ATCHK_CACHE','RE4DC_ATLIST_OVERFLOW','RE4DC_ATLIST_512'),v))
                          for v in ((0,0,0,0,0),(1,0,0,0,0),(1,1,0,0,0),(1,1,0,1,0),(1,1,1,1,0),(1,1,1,1,1),(1,2,2,1,1))],
             'effects':[dict(RE4DC_FX_SCAN=fx,RE4DC_ESP_OWNER=owner,RE4DC_PACE_TRANS_SKIP=pace)
                        for fx,owner,pace in ((0,0,0),(0,1,0),(0,2,1),(1,1,0),(1,1,1),(2,1,1))]}
    rows=[];frozen={};coverage=set()
    for kind,variants in configs.items():
        if a.only and kind!=a.only:continue
        values,files=fragments(kind);template=HERE/(kind+'_gap_fixture.cpp.in');common=HERE/'gap_common.hpp.in'
        files += [DEF,template,common,Path(__file__)]
        frozen.update({str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files})
        source=template.read_text().replace('@COMMON@',common.read_text())
        for name,value in values.items():source=source.replace('@'+name+'@',value)
        assert not re.search(r'@[A-Z0-9_]+@',source)
        cpp=out/(kind+'.cpp');cpp.write_text(source)
        for i,flags in enumerate(variants):
            arms=[]
            for audit in (0,1):
                name=f'{kind}-{i}-audit{audit}';binary=out/name
                cmd=['g++','-std=c++20','-O2','-fpermissive','-no-pie','-Wno-unused-function','-I',str(DEF.parent),
                     '-DRE4DC_FALLBACK_AUDIT35='+str(audit),*[f'-D{k}={v}' for k,v in flags.items()],str(cpp),'-o',str(binary)]
                if a.sanitize:cmd[2:3]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
                run=subprocess.run(cmd,capture_output=True,cwd=ROOT);(out/(name+'-compile.log')).write_bytes(run.stdout+run.stderr)
                if run.returncode:raise RuntimeError(run.stderr.decode())
                env=dict(os.environ)
                if a.sanitize:env.update(ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                run=subprocess.run([str(binary)],capture_output=True,env=env,cwd=ROOT)
                (out/(name+'.stdout')).write_bytes(run.stdout);(out/(name+'.stderr')).write_bytes(run.stderr)
                if run.returncode:raise RuntimeError(name+': '+run.stderr.decode())
                result=[json.loads(line) for line in run.stdout.splitlines()];assert result
                arms.append(result)
            assert [(r['case'],r['semantic']) for r in arms[0]]==[(r['case'],r['semantic']) for r in arms[1]],(kind,i,'behavior changed')
            assert all(not any(r['events']) for r in arms[0]),'disabled hooks emitted events'
            for r in arms[1]:coverage.update(names[j] for j,n in enumerate(r['events']) if n)
            rows.append(dict(kind=kind,options=flags,cases=len(arms[1]),checks=sum(r['checks'] for r in arms[1]),results=arms[1]))
    for name,digest in frozen.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name+' changed during test'
    report=dict(status='PASS',sanitize=a.sanitize,scope=__doc__,cases=sum(r['cases'] for r in rows),checks=sum(r['checks'] for r in rows),
                compositions=rows,covered_reasons=sorted(coverage),source_sha256=frozen,
                limits='Controlled external bindings and action callbacks. Full game, console timing and whole-image identity remain separate gates.')
    (out/'gap-host.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','sanitize','cases','checks','covered_reasons')}))


if __name__=='__main__':main()
