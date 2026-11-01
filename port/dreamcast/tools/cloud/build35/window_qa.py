#!/usr/bin/env python3
"""Build35 full existing QA snapshot/paging/transport capacity at max values.

Reuse Build29's actual-source QA extraction and controlled external observers,
with the current gap registry and a full exact window. This does not render a
console page or model network timing; every bounded transport byte is checked.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1];GAME=DC/'game'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m


def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    previous=load('qa35_previous',DC/'tools/d367/fallback_scan/test_qa29.py')
    extraction=load('qa35_extract',DC/'tools/cloud/build28/menu_contract.py')
    source=(GAME/'qa_menu.cpp').read_text()
    start=source.index('#if defined(RE4DC_DRAW_FALLBACK_AUDIT)',source.index('QaGame g_game;'))
    storage=source[start:source.index('constexpr int kLogLines',start)]
    start=source.index('int addf(int at, const char* fmt, ...) __attribute__')
    addf=source[start:source.index('#if defined(RE4DC_WORLD_SCRATCH)',start)]
    start=source.index('#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY)',source.index('void snap_diag()'))
    rows=source[start:source.index('#if defined(RE4DC_WORLD_METER)',start)]
    paging='\n'.join(extraction.function(source,name) for name in ('diag_page_rows','diag_rows','diag_pages'))
    prelude=replace_once(previous.PRELUDE,'#include "fallback_audit29.cpp"',
        '#include "fallback_audit29.cpp"\n#if RE4DC_FALLBACK_WINDOW35\n#include "fallback_window35.cpp"\n#endif')
    test=previous.TEST
    initial='''    d::begin_tick(UINT_MAX,UINT_MAX);f::begin_tick(UINT_MAX,UINT_MAX);
    for(unsigned i=0;i<d::ReasonCount;++i){d::hit(d::Reason(i),UINT_MAX);d::hit(d::Reason(i));}
    for(unsigned i=0;i<f::ReasonCount;++i){f::hit(f::Reason(i),UINT_MAX);f::hit(f::Reason(i));}
    d::end_tick();f::end_tick();'''
    test=replace_once(test,initial,'''    const unsigned repetitions=RE4DC_FALLBACK_WINDOW35?RE4DC_FALLBACK_WINDOW35:1;
    for(unsigned repeat=0;repeat<repetitions;++repeat){
        d::begin_tick(UINT_MAX-repeat,UINT_MAX);f::begin_tick(UINT_MAX-repeat,UINT_MAX);
        for(unsigned i=0;i<d::ReasonCount;++i){d::hit(d::Reason(i),UINT_MAX);d::hit(d::Reason(i));}
        for(unsigned i=0;i<f::ReasonCount;++i){f::hit(f::Reason(i),UINT_MAX);f::hit(f::Reason(i));}
        d::end_tick();f::end_tick();
    }
#if RE4DC_FALLBACK_WINDOW35
    // Maximum printed denominator widths, separately from semantic fixtures.
    re4dc::fw35::window.logic=re4dc::fw35::window.draws=re4dc::fw35::window.skipped=re4dc::fw35::window.incomplete=UINT64_MAX;
    re4dc::fw35::window.outside_room=UINT_MAX;
    re4dc::fw35::window.counter_overflow=true;
#endif''')
    old='''    for(unsigned i=0;i<d::ReasonCount;++i)assert(strstr(g_diag,(std::string(d::label(d::Reason(i)))+"=4294967295").c_str()));'''
    new='''    const std::string expected_draw=std::to_string(uint64_t(repetitions)*UINT32_MAX);
    for(unsigned i=0;i<d::ReasonCount;++i)assert(strstr(g_diag,(std::string(d::label(d::Reason(i)))+"="+expected_draw).c_str()));
#if RE4DC_FALLBACK_WINDOW35
    for(unsigned i=0;i<f::ReasonCount;++i)assert(strstr(g_diag,(std::string(f::label(f::Reason(i)))+"="+expected_draw).c_str()));
    assert(strstr(g_diag,"gpu_present=unobserved") && strstr(g_diag,"sums=drawn_only"));
#endif'''
    test=replace_once(test,old,new)
    # Enforce the actual QA producer's192-byte scratch, not just the fixture's320-byte actor scratch.
    test=replace_once(test,'    unsigned max_row=0;', '''    char compact[192];
    for(unsigned i=0;i<d::line_count();++i)assert(d::format_line(i,compact,sizeof(compact))>0);
    for(unsigned i=0;i<f::line_count();++i)assert(f::format_line(i,compact,sizeof(compact))>0);
    unsigned max_row=0;''')
    (out/'arch').mkdir();(out/'arch/irq.h').write_text('#pragma once\nextern "C" int irq_disable();\nextern "C" void irq_restore(int);\n')
    fixture=out/'qa35.cpp'
    fixture.write_text(prelude+storage+addf+'\nint append_audit_rows(int a){\n'+rows+'\nreturn a;}\n'+extraction.function(source,'snap_diag')+paging+test)
    helper=load('qa35_window_source',HERE/'window_host.py')
    files=[*helper.source_files(),Path(__file__),Path(previous.__file__),Path(extraction.__file__),GAME/'qa_menu.cpp',GAME/'draw_setup_audit.cpp',
        *[GAME/'platform/include'/name for name in ('fallback_actor_audit29.hpp','draw_fallback_link26.hpp','qa_link_review28.hpp')]]
    frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    profiles=[('gaps-only',1,0,1,1,1,1),('window-only',0,1,1,1,1,1),
        ('combined-standalone',1,32,0,0,0,0),('combined',1,32,1,1,1,0),('combined-max',1,64,1,1,1,1)]
    results=[]
    for name,gaps,n,dsa,xlu,fast,occ in profiles:
        binary=out/name
        flags=['-std=c++17','-O2','-Wall','-Wextra','-Wno-address','-Wno-misleading-indentation',
            '-I'+str(out),'-I'+str(GAME),'-DRE4DC_DRAW_FALLBACK_AUDIT=1','-DRE4DC_FALLBACK_AUDIT29=1',
            '-DRE4DC_FALLBACK_AUDIT35='+str(gaps),'-DRE4DC_FALLBACK_WINDOW35='+str(n),
            '-DRE4DC_WORLD_METER=1','-DRE4DC_DRAW_SETUP_AUDIT_HOST=1','-DRE4DC_DRAW_SETUP_AUDIT='+str(dsa),
            '-DRE4DC_DSA_XLU28='+str(xlu),'-DRE4DC_DSA_OCC28='+str(occ),'-DRE4DC_ACTOR_LIGHT_FAST_ONLY='+str(fast)]
        if args.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
        build=subprocess.run(['g++',*flags,str(fixture),'-o',str(binary)],capture_output=True)
        (out/(name+'-build.log')).write_bytes(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError(build.stderr.decode())
        env=dict(os.environ)
        if args.sanitize:env.update(ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        run=subprocess.run([str(binary)],capture_output=True,env=env)
        (out/(name+'-run.log')).write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(name,run.stdout.decode(),run.stderr.decode())
        results.append(dict(profile=name,gaps=gaps,N=n,**json.loads(run.stdout)));print('PASS',name,flush=True)
    assert frozen=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in frozen},'Source changed during QA gate'
    report=dict(status='PASS',scope=__doc__,sanitize=args.sanitize,profiles=results,source_sha256=frozen,
        coverage='Actual snap_diag/addf/audit rows/paging, all actor-attribution rows, DSA/XLU/OCC max fields, '
        'all91 FA29+gap reasons,133 DFA reasons, exact window max sums, normal and delayed/refused complete T/D reassembly.')
    (out/'window-qa.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',profiles=len(results),minimum_headroom=min(row['headroom'] for row in results))))


if __name__=='__main__':main()
