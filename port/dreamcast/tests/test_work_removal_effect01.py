"""Actual-source work-removal probes; public synthetic data only.

This is host evidence, not SH-4 binary identity, numeric/FPSCR qualification,
gameplay/STRICT acceptance, or a frame-time result. No private data is loaded.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[3]
BASE='65fe3d1f96ab269c136053725850101be9d3e692'
INC=ROOT/'port/dreamcast/game/platform/include'
HERE=Path(__file__).resolve().parent

def definition(text,name):
    # Skip prototypes; retain the actual production body and its conditional
    # compilation. The fixture never reproduces the selector/grid algorithm.
    pattern=re.compile(re.escape(name)+r'[^;{]*\{')
    match=pattern.search(text)
    if not match:raise AssertionError('definition missing: '+name)
    begin=text.rfind('\n',0,match.start())+1;brace=text.index('{',match.start());depth=1;end=brace+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[begin:end]

def struct_definition(text,name):
    return definition(text,'struct '+name)

def baseline(path,root):
    if root:return (root/path).read_text()
    return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)

def run(args,**kw):
    result=subprocess.run(args,capture_output=True,text=True,**kw)
    if result.returncode:raise AssertionError('command failed: '+repr(args)+'\n'+result.stdout+result.stderr)
    return result.stdout

def pp(text,flags):
    # Full recovered source off/PPC comparison, including downstream __LINE__.
    text=re.sub(r'^\s*#\s*include[^\n]*','',text,flags=re.M)
    text+='\nstatic const unsigned effect01_line_sentinel = __LINE__;\n'
    return run(['g++','-E','-P','-x','c++',*flags,'-'],input=text)

def make_checks(tmp):
    mk=ROOT/'port/dreamcast/game/work_removal_effect01.mk'
    text='OBJDIR := obj\nGAME_CPPFLAGS := unchanged\ninclude '+str(mk)+'\nobj/src/game/esp_sub.o:\n\t@printf \'%s\\n\' \'$(GAME_CPPFLAGS)\'\n'
    path=tmp/'Makefile';path.write_text(text)
    def make(*args,ok=True):
        result=subprocess.run(['make','--no-print-directory','-f',str(path),*args],capture_output=True,text=True)
        assert (result.returncode==0)==ok,(args,result.stdout,result.stderr)
        return result.stdout.strip()
    assert make()=='unchanged'
    assert make('EFFECT_RECORD_PASS01=0','ESP1B_EDGE_REUSE01=0')=='unchanged'
    assert make('EFFECT_RECORD_PASS01=1')=='unchanged -DRE4DC_EFFECT_RECORD_PASS01=1'
    deps=['ESP1B_GRID03=1','EFFECT_UV12=1','NATIVE_DRAW_OUTCOMES=1']
    assert make('ESP1B_EDGE_REUSE01=1',*deps)=='unchanged -DRE4DC_ESP1B_EDGE_REUSE01=1'
    for knob in ('EFFECT_RECORD_PASS01','ESP1B_EDGE_REUSE01'):
        for bad in ('','2','-1','word','0 1','1 '):make(knob+'='+bad,ok=False)
    for dep in deps:
        make('ESP1B_EDGE_REUSE01=1',*[d for d in deps if d!=dep],ok=False)
    # Each prerequisite must be exactly one; concatenating values could admit
    # ambiguous assignments such as GRID=11, UV=empty, OUTCOMES=1.
    for values in (('11','','1'),('','11','1'),('1','','11'),('1','1','1 0')):
        make('ESP1B_EDGE_REUSE01=1',*[d.split('=')[0]+'='+v for d,v in zip(deps,values)],ok=False)
    return {'default_flags_unchanged':True,'invalid_values_and_missing_dependencies_rejected':True}

def archive_fixture(tmp):
    spec=importlib.util.spec_from_file_location('effect01_codec',ROOT/'port/dreamcast/tools/compact_effect_records.py')
    codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
    records=[]
    for effect,kind in ((11,0),(14,0),(11,1),(11,2)):
        rec=bytearray(300);rec[1]=effect;rec[264]=kind
        for at,value in ((12,0x80000000),(16,0x7fc12345),(40,0x3f123456)):
            struct.pack_into('<I',rec,at,value)
        records.append(rec)
    seq=struct.pack('<H',len(records))+bytes(46)+b''.join(records);seq+=bytes((-len(seq))%32)
    ranges,entries=codec.prepare_sequences([(64,seq,'public/est')],'public')
    body=bytearray(64)+ranges[0][2];off=len(body)
    index=codec.identity_index(entries,lambda n:n,len(body)+128);assert len(index)==64
    body+=index+bytes(64);struct.pack_into('<2I',body,0,2,len(body)-64)
    struct.pack_into('<2I',body,16,64,off);body[24:32]=b'EFF\0ESQ\0'
    (tmp/'fixture.arc').write_bytes(body);(tmp/'reference.bin').write_bytes(seq)

def select_checks(tmp,old_source,new_source):
    (tmp/'kos').mkdir(exist_ok=True)
    (tmp/'kos.h').write_text('#pragma once\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n')
    (tmp/'kos/net.h').write_text('#pragma once\n#include <cstdint>\nstd::uint32_t net_crc32le(const std::uint8_t*,int);\n')
    (tmp/'re4dc_platform.h').write_text('#pragma once\nextern "C" void re4dc_log(const char*,...);\nextern "C" void re4dc_missing(const char*);\n')
    esp=(ROOT/'include/esp.h').read_text()
    records=esp[esp.index('struct EspGenPrmW'):esp.index('// Texture animation data')]
    info=struct_definition(esp,'EspInfo')+';'
    template=(HERE/'work_removal_effect01_select.cpp.in').read_text().replace('@RECORD_TYPES@',records).replace('@INFO_TYPE@',info)
    archive_fixture(tmp);executables={};results={}
    for label,source,flag,decodes in [('baseline',old_source,None,2),('implicit0',new_source,None,2),('explicit0',new_source,0,2),('enabled',new_source,1,1)]:
        text=template.replace('@SELECT_FUNCTION@',definition(source,'int EspEstSetSelect('))
        file=tmp/'select.cpp';file.write_text(text);exe=tmp/'select'
        flags=[] if flag is None else ['-DRE4DC_EFFECT_RECORD_PASS01='+str(flag)]
        run(['g++','-std=c++17','-O1','-ffp-contract=off','-ffile-prefix-map='+str(tmp)+'=/work-removal-effect01','-DRE4DC_GAME','-DRE4DC_OB_DECODE=1',*flags,
             '-I'+str(tmp),'-I'+str(INC),str(file),str(ROOT/'port/dreamcast/game/platform/native_effect.cpp'),'-lz','-o',str(exe)])
        executables[label]=exe.read_bytes()
        results[label]=json.loads(run([str(exe),str(tmp/'fixture.arc'),str(tmp/'reference.bin'),str(decodes)]))
    assert executables['baseline']==executables['implicit0']==executables['explicit0']
    results['disabled_host_elf_sha256']=hashlib.sha256(executables['baseline']).hexdigest()
    return results

def grid_checks(tmp,old_source,new_source,old_grid,new_grid):
    flags=['-DRE4DC_GAME','-DRE4DC_FX_STRIP21=1','-DRE4DC_NATIVE_DRAW_OUTCOMES=1']
    assert pp(old_grid,flags)==pp(new_grid,flags)
    assert pp(old_grid,flags)==pp(new_grid,flags+['-DRE4DC_ESP1B_EDGE_REUSE01=0'])
    assert pp(old_grid,flags+['-D__PPC__'])==pp(new_grid,flags+['-D__PPC__','-DRE4DC_ESP1B_EDGE_REUSE01=1'])
    work=struct_definition(new_source,'Esp1bSpWork')+';'
    getpos=definition(new_source,'void GetPosXY(').replace('void GetPosXY(', 'void SourceGetPosXY01(',1)
    template=(HERE/'work_removal_effect01_grid.cpp.in').read_text().replace('@WORK_TYPE@',work).replace('@GETPOS_FUNCTION@',getpos)
    (tmp/'grid-reference01.inc').write_text(old_grid)
    file=tmp/'grid.cpp';file.write_text(template);exe=tmp/'grid'
    executables={};results={}
    for label,source,flag in [('baseline',old_grid,None),('implicit0',new_grid,None),('explicit0',new_grid,0),('enabled',new_grid,1)]:
        (tmp/'grid-candidate01.inc').write_text(source)
        control=[] if flag is None else ['-DRE4DC_ESP1B_EDGE_REUSE01='+str(flag)]
        run(['g++','-std=c++20','-O2','-ffp-contract=off','-ffile-prefix-map='+str(tmp)+'=/work-removal-effect01',*flags,*control,
             '-I'+str(tmp),'-I'+str(INC),str(file),'-o',str(exe)])
        executables[label]=exe.read_bytes();results[label]=json.loads(run([str(exe),str(int(flag==1))]))
    assert executables['baseline']==executables['implicit0']==executables['explicit0']
    results['disabled_host_elf_sha256']=hashlib.sha256(executables['baseline']).hexdigest()
    # The actual modified function is exercised once under ASan/UBSan for the
    # same cases, addressing the new in-place corner copies and boundary exits.
    sanitized=tmp/'grid-sanitized'
    run(['g++','-std=c++20','-O1','-ffp-contract=off','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
         *flags,'-DRE4DC_ESP1B_EDGE_REUSE01=1','-I'+str(tmp),'-I'+str(INC),str(file),'-o',str(sanitized)])
    # LeakSanitizer cannot inspect /proc task state in the managed sandbox.
    # This check targets access/undefined behavior; no production allocation
    # was added. Keep ASan/UBSan on and explicitly omit the leak detector.
    env=dict(os.environ,ASAN_OPTIONS=os.environ.get('ASAN_OPTIONS','')+':detect_leaks=0')
    assert json.loads(run([str(sanitized),'1'],env=env))==results['enabled']
    results['asan_ubsan']='pass; leak detection disabled (restricted /proc)'
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--baseline-root',type=Path)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    old=baseline('src/game/esp_sub.cpp',args.baseline_root);new=(ROOT/'src/game/esp_sub.cpp').read_text()
    for flags in (['-DRE4DC_GAME'],['-DRE4DC_GAME','-DRE4DC_ESP1B_GRID03=1','-DRE4DC_EFFECT_MASK12=1','-DRE4DC_EFFECT_SPRITES=1','-DRE4DC_EFFECT_LEAN=1','-DRE4DC_FX_STRIP21=1','-DRE4DC_NATIVE_DRAW_OUTCOMES=1']):
        expected=pp(old,flags)
        assert pp(new,flags)==expected
        assert pp(new,flags+['-DRE4DC_EFFECT_RECORD_PASS01=0','-DRE4DC_ESP1B_EDGE_REUSE01=0'])==expected
    ppc=['-DRE4DC_GAME','-D__PPC__']
    assert pp(old,ppc)==pp(new,ppc+['-DRE4DC_EFFECT_RECORD_PASS01=1'])
    old_grid=baseline('port/dreamcast/game/platform/include/esp1b_grid03.inc',args.baseline_root)
    new_grid=(INC/'esp1b_grid03.inc').read_text()
    with tempfile.TemporaryDirectory(prefix='work-removal-effect01-') as directory:
        tmp=Path(directory)
        report={'source_base':BASE,'evidence':'host actual-source only; target/runtime/console pending',
                'full_source_off_ppc_preprocessing':'identical','make':make_checks(tmp),'select':select_checks(tmp,old,new),
                'grid':grid_checks(tmp,old,new,old_grid,new_grid)}
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
