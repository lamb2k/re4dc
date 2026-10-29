#!/usr/bin/env python3
"""Exercise actual portal runtime, chunk emitter and queued flush receipt block.

Synthetic package/geometry and controlled emit_pick/PVR edges test lifecycle,
not authored occluder correctness, GPU completion, look, STRICT or console cost.
"""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];PLATFORM=ROOT/'port/dreamcast/game/platform'
spec=importlib.util.spec_from_file_location('extract',ROOT/'port/dreamcast/tools/d367/world_submit_spike/check_runtime.py');extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)
def between(s,a,b):
    at=s.index(a)+len(a);return s[at:s.index(b,at)]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source=(PLATFORM/'native_static.cpp').read_text()
    core=source[source.index('inline void setup_state(State& st,'):source.index('State& trans_state();',source.index('inline void setup_state(State& st,'))]
    (a.output/'portal29_pc_core.inc').write_text(core)
    base=(HERE/'portal_runtime_fixture.cpp').read_text()
    base='#define RE4DC_WORLD_PORTAL_COMPLETION 1\n'+base
    base=base.replace('struct SelectStats {','struct SelectStats {unsigned strips_clipped=0,strips_culled=0;')
    base=base.replace('int main(){','void original_checks(){',1).replace('wp29::finish(', 'fixture_finish(')
    before="""void fixture_finish(unsigned placement,unsigned part,bool success,const unsigned*){
    const auto& m=meta[part];const unsigned key[6]={m.crc,m.fnv,m.width,m.height,m.pass,m.cull};
    wp29::finish(wp29::capture(placement,part,key),re4dc::portal29::Completion::emitted(success?1:0,success,2,success?2:0,success),key);
}
"""
    base=base.replace('void original_checks(){',before+'void original_checks(){',1)
    # Fixture opaque prerequisite additionally verifies that receipt publication
    # happens outside the borrowed SQ lock.
    base=base.replace('int re4dc_pvs23_opaque_ready(', 'static bool fixture_sq_held=false;\nint re4dc_pvs23_opaque_ready(',1).replace('return opaque_ok && key && !key[4];','return !fixture_sq_held && opaque_ok && key && !key[4];')
    extra=(HERE/'portal_completion_fixture.cpp.in').read_text().replace('static bool sq_held=false;','static bool& sq_held=fixture_sq_held;')
    values={'CHUNK_EMIT':extract.function(source,'    __attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){'), 'FLUSH':between(source,'// PORTAL_COMPLETION_FLUSH_BEGIN','// PORTAL_COMPLETION_FLUSH_END')}
    for k,v in values.items():extra=extra.replace('@'+k+'@',v)
    assert not re.search(r'@[A-Z_]+@',extra)
    cpp=a.output/'completion.cpp';cpp.write_text(base+'\n'+extra);binary=a.output/'completion'
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Wno-misleading-indentation','-Wno-unused-parameter','-Wno-unused-variable']
    if a.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
    cmd=['g++',*flags,'-I',str(PLATFORM/'include'),'-I',str(a.output),str(cpp),'-o',str(binary)]
    run=subprocess.run(cmd,capture_output=True);(a.output/'compile.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,run.stderr.decode()
    run=subprocess.run([str(binary)],capture_output=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'));(a.output/'run.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,run.stderr.decode()
    files=[PLATFORM/'native_static.cpp',PLATFORM/'include/world_portal29.hpp',PLATFORM/'include/world_portal29_runtime.inc',HERE/'portal_runtime_fixture.cpp',HERE/'portal_completion_fixture.cpp.in',Path(__file__)]
    report=dict(status='PASS',scope=__doc__,sanitize=a.sanitize,output=run.stdout.decode(),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in values.items()})
    (a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(run.stdout.decode(),end='')
if __name__=='__main__':main()
