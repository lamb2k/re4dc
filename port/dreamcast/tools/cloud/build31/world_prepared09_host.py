#!/usr/bin/env python3
"""Exercise actual plan lifecycle and early-placement consumer with controlled owners.

The production plan runtime, actual early consumer block and literal old
world_box are compiled. This is synthetic lifetime/layout/cull-order evidence,
not real-cell proof, full rendering/selection math, gameplay or console cost.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];PLATFORM=ROOT/'port/dreamcast/game/platform'
spec=importlib.util.spec_from_file_location('extract',ROOT/'port/dreamcast/tools/d367/world_submit_spike/check_runtime.py');extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 source=(PLATFORM/'native_static.cpp').read_text();start=source.index('// WORLD_PREPARED09_EARLY_BEGIN')+len('// WORLD_PREPARED09_EARLY_BEGIN');end=source.index('// WORLD_PREPARED09_EARLY_END',start)
 values={'EARLY':source[start:end],'WORLD_BOX':extract.function(source,'inline void world_box(')}
 at=source.index('            const auto* plan_part=plan?plan+k:nullptr;');stop=source.index('            if(plan_part)++wplan29::planned;else ++wplan29::legacy;',at)+len('            if(plan_part)++wplan29::planned;else ++wplan29::legacy;')
 values['METADATA']=source[at:stop]
 guard=source.rindex('#if RE4DC_WORLD_PREPARED09',0,at);guard_end=source.index('#endif',guard)+len('#endif')
 values['RECORD_GUARD']=source[guard:guard_end]
 assert 're4dc_model_packet_abort' in values['RECORD_GUARD'] and source.count('if(plan && !wplan29::current(plan_incarnation))')==4
 fixture=(HERE/'world_prepared09_fixture.cpp.in').read_text()
 for k,v in values.items():fixture=fixture.replace('@'+k+'@',v)
 cpp=a.output/'prepared.cpp';cpp.write_text(fixture)
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Wno-unused-variable','-Wno-unused-parameter']
 if a.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
 binary=a.output/'prepared';command=['g++',*flags,'-I',str(PLATFORM/'include'),str(cpp),'-o',str(binary)]
 run=subprocess.run(command,capture_output=True);(a.output/'compile.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,run.stderr.decode()
 run=subprocess.run([str(binary)],capture_output=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'));(a.output/'run.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,run.stderr.decode()
 # Compile the existing ordered live-policy oracle with the new portable
 # helpers present, plus exhaustive actual indexed lookup boundary cases.
 extra_results={}
 for name,file in [('index','world_prepared09_index.cpp'),('policy','part_plan_host.cpp')]:
  exe=a.output/name;cmd=['g++',*flags,'-DRE4DC_WORLD_PREPARED09=1','-I',str(PLATFORM/'include'),str(HERE/file),'-o',str(exe)]
  result=subprocess.run(cmd,capture_output=True);(a.output/(name+'-compile.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr.decode()
  result=subprocess.run([str(exe)],capture_output=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'));(a.output/(name+'-run.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0,result.stderr.decode();extra_results[name]=result.stdout.decode()
 # Actual Make dependency and early source guard: no SDK/private inputs.
 makefile=a.output/'guard.mk';makefile.write_text('OBJDIR:=unused\ninclude '+str(ROOT/'port/dreamcast/game/world_plan29.mk')+'\nall:\n\t@echo $(WORLD_PREPARED09)\n')
 supported=['WORLD_PREPARED09=1','WORLD_PART_PLAN29=1','NATIVE_PKG_HIGH=1','PS2_WORLD_MESH=1','MOVIE_WORLD_ARENA=1','STATIC_OBJ_LIFETIME05=1']
 cases=[('absent',[],True),('zero',['WORLD_PREPARED09=0'],True),('supported',supported,True)]
 cases += [('invalid-'+str(i),supported+['WORLD_PREPARED09='+v],False) for i,v in enumerate(('','2','-1','0 1'))]
 cases += [(name,supported+[name+'=0'],False) for name in ('WORLD_PART_PLAN29','MOVIE_WORLD_ARENA','STATIC_OBJ_LIFETIME05')]
 guards=[]
 for name,args,accepted in cases:
  result=subprocess.run(['make','--no-print-directory','-f',str(makefile),'all',*args],capture_output=True)
  assert (result.returncode==0)==accepted,(name,result.stderr.decode());guards.append(dict(name=name,accepted=accepted))
 files=[PLATFORM/'native_static.cpp',PLATFORM/'include/world_part_plan29.hpp',PLATFORM/'include/world_part_plan29_runtime.inc',ROOT/'port/dreamcast/game/world_plan29.mk',HERE/'world_prepared09_fixture.cpp.in',HERE/'world_prepared09_index.cpp',HERE/'part_plan_host.cpp',Path(__file__)]
 report=dict(status='PASS',scope=__doc__,sanitize=a.sanitize,output=run.stdout.decode(),extra_results=extra_results,guards=guards,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in values.items()})
 (a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(run.stdout.decode(),end='')
if __name__=='__main__':main()
