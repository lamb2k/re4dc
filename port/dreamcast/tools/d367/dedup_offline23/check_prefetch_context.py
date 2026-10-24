#!/usr/bin/env python3
"""Host-only actual-source prefetch/SDO3 decoder-context and clipping controls.

Compiler scratch stays in explicit /dev/shm output. No SDK, target or guest claim.
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
from check_composition import generate

CONTEXT = r'''
static void prefetch_context_case(){
    auto data=composition_package();re4dc::room::MeshPackage package;
    assert(package.adopt(data.data(),unsigned(data.size()),true,true));
    QueuePart part;re4dc::room::CompactVertex12 gather[256]{};
    MeshDraw e{{part,{},1.0f,1000.0f},package,package.parts()[0],lut,gather};
    e.gathered=gather;
    // Encoded first, ordinary plain, indexed, indexed zero pick, new encoded
    // material and another encoded pick. Every call must set OR clear context.
    const unsigned lets[]={0,4,6,7,8,12},nr[]={255,255,255,0,1,255};
    unsigned material[6]={1,2,128,128,0,0};
    for(unsigned j=0;j<6;++j){
        material[0]=j+1;material[1]=2*j+7;e.ps2=material;
        part.uv_offset[0]=float(j)*.125f;part.cull=j%3;
        const auto& l=package.meshlets()[lets[j]];
        MeshDraw::Pick pk{std::uint16_t(lets[j]),std::uint8_t(nr[j]),2,1,3,{0,0}};
        const auto* got=e.emit_corners(l,pk);
        const unsigned rep=package.repeat_count(l);
        const auto* base=package.vertices()+l.first_vertex;
        assert(e.dd_base==(rep?base:nullptr));
        assert(e.dd_unique==l.vertex_count-rep&&e.dd_count==l.vertex_count);
        assert(e.dd_active(e.dd_word(l))==bool(rep));
        if(!package.indexed(l))assert(got==base);else assert(got==gather);
        assert(e.ps2==material&&part.cull==j%3);
    }
    std::puts("PASS encoded-first/plain/indexed/zero/new-material decoder context");
}
'''

def sha(b):return hashlib.sha256(b).hexdigest()

def prefetch_region(raw):
    a=raw.index('// SCENERY_EMIT_PREFETCH_MEMBERS_BEGIN')
    a=raw.index('\n',a)+1
    return raw[a:raw.index('// SCENERY_EMIT_PREFETCH_MEMBERS_END',a)]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-tree',type=Path,required=True)
    ap.add_argument('--baseline-native',type=Path,required=True,help='Frozen4be native_static.cpp, read-only')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();tree=args.source_tree.resolve();out=args.output.resolve()
    if not out.is_relative_to(Path('/dev/shm')):raise ValueError('RAM output required')
    out.mkdir(parents=True,exist_ok=False)
    raw=(tree/'port/dreamcast/game/platform/native_static.cpp').read_text()
    source,values,_=generate(tree);region=prefetch_region(raw)
    source=source.replace(values['EMIT_PICK'],region+'\n'+values['EMIT_PICK'])
    old='__attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){'
    assert source.count(old)==1
    source=source.replace(old,'__attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n,const Pick* following=nullptr){')
    source=source.replace('int main(int argc,char** argv){',CONTEXT+'\nint main(int argc,char** argv){')
    seam='if(id>=100){queue_case(id);report(id);return 0;}'
    assert source.count(seam)==1
    source=source.replace(seam,'if(id==200){prefetch_context_case();return 0;}\n    '+seam)
    cpp=out/'prefetch.cpp';cpp.write_text(source)
    for name,text in {'dc/pvr.h':'#pragma once\n','kos/fs.h':'#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n','dc/matrix.h':'#pragma once\nusing matrix_t=float[4][4];\nstatic void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}\nstatic void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}\n'}.items():
        path=out/'shim'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    env=dict(os.environ,TMPDIR='/dev/shm',PYTHONDONTWRITEBYTECODE='1')
    def build(label,decoded,replay,batch,src=cpp):
        binary=out/label
        cmd=['g++','-std=c++20','-O2','-ffp-contract=off','-DRE4DC_SCENERY_SELECT_ONLY=1',f'-DRE4DC_SCENERY_SUBMIT_BATCH={batch}',f'-DRE4DC_SCENERY_REPLAY_LEAN={replay}',f'-DCOMPOSITION_DECODED={decoded}','-DCHECK_DIAGNOSTICS=0','-DRE4DC_SCENERY_SELECT_LEAN2=0','-DRE4DC_SCENERY_EMIT_PREFETCH=1','-I'+str(out/'shim'),'-I'+str(tree/'port/dreamcast/game/platform/include'),str(src),'-o',str(binary)]
        run=subprocess.run(cmd,capture_output=True,env=env);(out/(label+'.compile.log')).write_bytes(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError((label,run.stderr.decode()))
        return binary
    records={};context={};comparisons=0
    for batch in (0,1):
        for decoded in (0,1):
            for replay in (0,1):
                label=f'b{batch}-d{decoded}-r{replay}';binary=build(label,decoded,replay,batch);rows=[]
                c=subprocess.run([str(binary),'200'],capture_output=True,env=env)
                if c.returncode:raise RuntimeError((label,'context',c.returncode,c.stderr.decode()))
                context[label]=c.stdout.decode().strip()
                for case in range(100,112):
                    c=subprocess.run([str(binary),str(case)],capture_output=True,env=env)
                    if c.returncode or len(c.stdout.splitlines())!=3 or not re.search(rb'lock=(\d+) unlock=\1',c.stderr):raise RuntimeError((label,case,c.returncode))
                    rows.append(c.stdout)
                records[label]=b''.join(rows);(out/(label+'.stdout')).write_bytes(records[label])
                if replay:
                    assert records[label]==records[f'b{batch}-d{decoded}-r0'],'replay differs';comparisons+=12
                if decoded:
                    assert records[label]==records[f'b{batch}-d0-r{replay}'],'encoded differs';comparisons+=12
    mutants={}
    block='''#if RE4DC_SCENERY_DEDUP==3
        // Match corners(): refresh or clear the decoder before every early return.
        const unsigned rep=package.repeat_count(l);
        dd_base=rep?base:nullptr;dd_unique=l.vertex_count-rep;dd_count=l.vertex_count;
#endif'''
    assert region.count(block)==1
    for name,bad in [('missing-refresh',region.replace(block,'')),('stale-reset',region.replace('dd_base=rep?base:nullptr;','if(rep)dd_base=base;'))]:
        mutant=out/(name+'.cpp');mutant.write_text(source.replace(region,bad));binary=build(name,0,0,0,mutant)
        c=subprocess.run([str(binary),'200'],capture_output=True,env=env)
        assert c.returncode!=0,(name,'mutation escaped')
        mutants[name]=dict(returncode=c.returncode,stderr=c.stderr.decode().strip())
    # The sole runtime change is inside an already default-off prefetch block.
    # Actual C preprocessing of that entire changed region must erase it at0.
    preprocessed=[]
    for label,r in [('baseline',prefetch_region(args.baseline_native.read_text())),('fixed',region)]:
        c=subprocess.run(['g++','-E','-P','-x','c++','-DRE4DC_SCENERY_EMIT_PREFETCH=0','-DRE4DC_SCENERY_DEDUP=3','-'],input=('#if RE4DC_SCENERY_EMIT_PREFETCH\n'+r+'\n#endif\n').encode(),capture_output=True,env=env)
        assert c.returncode==0;preprocessed.append(c.stdout)
    assert preprocessed[0]==preprocessed[1]==b''
    report=dict(status='PASS_HOST_PREFETCH_DEDUP_CONTEXT_ONLY',source_head=subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip(),native_source_sha256=sha(raw.encode()),helper_sha256=sha(Path(__file__).read_bytes()),generated_cpp_sha256=sha(source.encode()),prefetch_region_sha256=sha(region.encode()),comparisons=comparisons,context_controls=context,mutants=mutants,output_sha256={k:sha(v) for k,v in records.items()},prefetch0_changed_region_preprocessed_identical=True,prefetch0_preprocessed_sha256=sha(preprocessed[0]),temporary_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),scope='Actual extracted methods, portable clipping and real reader on synthetic admitted packages; two FMAC host-arithmetic edges. No target/programme/guest/pixels/performance qualification; PREFETCH0 proof covers changed region, not a new whole-programme build.')
    (out/'prefetch-context-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','comparisons','prefetch0_changed_region_preprocessed_identical','temporary_bytes')}))

if __name__=='__main__':main()
