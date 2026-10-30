#!/usr/bin/env python3
"""Actual world direct-strip scratch admission; public synthetic assets only.

Reuses Build12's extracted production bind/emitter and portable SQ arithmetic
boundaries. Complete TA words are compared; no SH4 codegen, timing or live scene
acceptance is inferred. OFF preprocess/object identity is a hosted emitter
control, not a target/full-image identity claim.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
GAME=ROOT/'port/dreamcast/game'
NATIVE=GAME/'platform/native_static.cpp'
BASE='83148f45e7cc98032c724b0d9309737e16806ae5'
spec=importlib.util.spec_from_file_location('route_b12',HERE.parent/'build12/check_emitter.py')
b12=importlib.util.module_from_spec(spec);spec.loader.exec_module(b12)

def sha(data):return hashlib.sha256(data).hexdigest()

def source(raw):
    read=Path.read_text
    extract=b12.prior.original.function
    def exact_function(body,signature):
        if signature=='auto chunk_flush=[&]()->int':
            # Alternate portal branches have mutually exclusive opening
            # braces. The enclosing producer has an exact source seam.
            start=body.index(signature)
            end=body.index('\n    };\n#endif\n    const float px_x=',start)
            return body[start:end+len('\n    }')]
        return extract(body,signature)
    with patch.object(Path,'read_text',lambda p,*a,**kw:raw if p==NATIVE else read(p,*a,**kw)), \
         patch.object(b12.prior.original,'function',side_effect=exact_function):
        text,parts=b12.sources()
    text='''#ifndef RE4DC_WORLD_ROUTE_SCRATCH31
#define RE4DC_WORLD_ROUTE_SCRATCH31 0
#endif
#define RE4DC_GCA_MODEL_TEXTURE(...) ((void)0)
#define RE4DC_GCA_MODEL_ACCEPT(...) ((void)0)
#define RE4DC_GCA_MODEL_PREPARE(...) ((void)0)
#define RE4DC_PART_DUMP_KEY(...) ((void)0)
#define DFA26_COUNT(...) ((void)0)
#define RE4DC_PROFILE_SCOPE(...) ((void)0)
#define RE4DC_MESH_CLASSIFY 0
'''+text
    sq_header='#include "'+str(ROOT/'port/dreamcast/room/scenery_direct_strips.hpp')+'"'
    assert text.count(sq_header)==1
    text=text.replace(sq_header,sq_header+'''
// Existing portable vertex-copy helper at the SH4-only SQ transport boundary.
namespace re4dc::vp {
static std::uint32_t* emit_sq(std::uint32_t* sq,const pvr_vertex_t* cache,const std::uint8_t* indices,unsigned n){
    auto* first=reinterpret_cast<pvr_vertex_t*>(sq);auto* last=emit(first,cache,indices,n);
    for(auto* v=first;v<last;++v)sq_flush(reinterpret_cast<std::uint32_t*>(v));
    return reinterpret_cast<std::uint32_t*>(last);
}
}
''')
    # This standalone route profile does not select strip-group subranges.
    # Keep the complete production draw/meshlet bodies and source guards.
    text=text.replace('#define RE4DC_PS2_STRIP_GROUPS 1','#define RE4DC_PS2_STRIP_GROUPS 0')
    text=text.replace('unsigned prime_reuse=0,prime_bad=0;',
                      'unsigned prime_reuse=0,prime_bad=0,skipped=0,check_bad=0;')
    # Full current producer bodies execute with the source generation check.
    # Other legacy fixture functions remain in their original unmutated profile.
    pick=parts['EMIT_PICK']
    text=text.replace(pick,'#define RE4DC_WORLD_MUTATION31 1\n'+pick+'\n#undef RE4DC_WORLD_MUTATION31')
    mutation=b12.prior.function(raw,'bool mutation_current()const')
    helper=b12.prior.function(raw,'void prepare_route_constants()') if 'void prepare_route_constants()' in raw else ''
    insertion='unsigned mutation_epoch=1;\n'+mutation+'\n#if RE4DC_WORLD_ROUTE_SCRATCH31\n'+helper+'\n#endif\n'
    immediate=b12.prior.function(raw,'int draw(const RE4DC_SCENERY_RECORD& l')
    meshlet=b12.prior.function(raw,'int meshlet(const RE4DC_SCENERY_RECORD& l')
    insertion+='\n'+meshlet+'\n#define RE4DC_WORLD_MUTATION31 1\n'+immediate+'\n#undef RE4DC_WORLD_MUTATION31\n'
    stats=re.search(r'static struct \{unsigned (.+?);\}stats;',text).group()
    names=sorted(set(re.findall(r'\bstats\.(\w+)',immediate+meshlet+text)))
    text=text.replace(stats,'static struct {unsigned '+','.join(name+'=0' for name in names)+';}stats;')
    assert text.count(parts['BORROW_GATHER'])==1
    text=text.replace(parts['BORROW_GATHER'],insertion+parts['BORROW_GATHER'])
    prefix='static bool route_mutation_current=true,route_mutate_on_bind=false;\nstatic unsigned route_packet_capacity=0;\nstatic bool worldPackageSelectionCurrent(unsigned epoch){return epoch==1 && route_mutation_current;}\n'
    # This is a controlled publisher callback at the actual binding I/O edge.
    needle='++acquired;'
    assert text.count(needle)==1
    text=text.replace(needle,'if(route_mutate_on_bind)route_mutation_current=false;\nif(route_packet_capacity)model_pending=kModelPacketBytes/32-route_packet_capacity;'+needle)
    at=text.index('static void sourceWorldTextureAcquired(')
    text=text[:at]+prefix+text[at:]
    case=(HERE/'world_route_scratch31.cpp.in').read_text()
    case=case[case.index('static void route_case('):]
    text=text.replace('static std::uint64_t digest(',case+'\nstatic std::uint64_t digest(',1)
    marker='int main(int argc,char** argv){'
    assert text.count(marker)==1
    text=text.replace(marker,marker+'\nif(argc==4 && !std::strcmp(argv[1],"route")){for(unsigned i=0;i<8;++i)seed(i,0,0);route_case(unsigned(std::strtoul(argv[2],nullptr,10)),argv[3]);return 0;}')
    bounds=b12.prior.function((ROOT/'port/dreamcast/room/pvr_geometry.cpp').read_text(),'bool group_visible(')
    text+='\nnamespace re4dc::render {\n'+bounds+'\n}\n'
    return text

def run(cmd,*,env=None):
    p=subprocess.run([str(x) for x in cmd],cwd=ROOT,capture_output=True,env=env)
    assert p.returncode==0,(cmd,p.stderr.decode()[-10000:])
    return p

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    watched=[NATIVE,GAME/'platform/native_ui.cpp',GAME/'scenery_data_variants.mk',Path(__file__),HERE/'world_route_scratch31.cpp.in',
        HERE.parent/'build12/check_emitter.py',HERE.parent/'build12/fixtures.py',HERE.parent/'build12/fixture_emitter.cpp.in',
        HERE.parent/'build5/check_geometry.py',HERE.parent/'build5/fixture_geometry.cpp.in',
        ROOT/'port/dreamcast/tools/d367/world_replay_lean/fixture_boundary.cpp.in',
        ROOT/'port/dreamcast/tools/d367/world_submit_spike/check_runtime.py',
        ROOT/'port/dreamcast/tools/scenery_data_variants.py',ROOT/'port/dreamcast/tools/convert_room_bins.py']
    watched+=[ROOT/'port/dreamcast/room'/name for name in ('scenery_data_variants.hpp','scenery_direct_strips.hpp',
        'mesh_fastpath.hpp','mesh_fastpath_sched.hpp','pvr_geometry.cpp','pvr_geometry.hpp','instanced_mesh.hpp')]
    frozen={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in watched}
    (out/'shim/dc').mkdir(parents=True);(out/'shim/kos').mkdir()
    (out/'shim/dc/pvr.h').write_text('#pragma once\n')
    (out/'shim/kos/fs.h').write_text('#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n')
    (out/'shim/dc/matrix.h').write_text('#pragma once\nusing matrix_t=float[4][4];\nstatic void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}\nstatic void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}\n')
    raw=NATIVE.read_text();baseline=subprocess.check_output(['git','show',BASE+':'+str(NATIVE.relative_to(ROOT))],cwd=ROOT).decode()
    flags=['g++','-std=c++20','-O2','-ffp-contract=off','-ffile-prefix-map='+str(out)+'=fixture',
        '-DRE4DC_SCENERY_SUBMIT_BATCH=1','-DRE4DC_SCENERY_REPLAY_LEAN=1','-DRE4DC_SCENERY_UV_SNAPSHOT=1',
        '-DRE4DC_SCENERY_SELECT_ONLY=1','-DRE4DC_SCENERY_SELECT_LEAN2=0','-DRE4DC_SCENERY_EMIT_PREFETCH=0',
        '-DRE4DC_SCENERY_LOCAL_INDEXED=0','-DRE4DC_SCENERY_DIRECT_STRIPS=1','-DB12_TA_HASH=0','-DCHECK_DIAGNOSTICS=0',
        '-I'+str(out/'shim'),'-I'+str(GAME/'platform/include')]
    if a.sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    binaries={};identities={}
    for name,body,extra in [('baseline',baseline,[]),('absent',raw,[]),('zero',raw,['-DRE4DC_WORLD_ROUTE_SCRATCH31=0']),('on',raw,['-DRE4DC_WORLD_ROUTE_SCRATCH31=1'])]:
        cpp=out/(name+'.cpp');cpp.write_text(source(body));exe=out/name
        built=subprocess.run([*flags,*extra,str(cpp),'-o',str(exe)],cwd=ROOT,capture_output=True)
        (out/(name+'.compile.log')).write_bytes(built.stdout+built.stderr)
        assert built.returncode==0,(name,built.stderr.decode()[-12000:])
        binaries[name]=exe
        # Same stdin name and preprocessed input remove source/output paths
        # from this hosted absent/zero/baseline object comparison.
        pp=subprocess.run([*flags,*extra,'-E','-P','-x','c++','-'],input=cpp.read_bytes(),cwd=ROOT,capture_output=True)
        assert pp.returncode==0,pp.stderr.decode()
        obj=subprocess.run([*flags,'-c','-x','c++','-','-o',str(out/(name+'.o'))],input=pp.stdout,cwd=ROOT,capture_output=True)
        assert obj.returncode==0,obj.stderr.decode()[-5000:]
        identities[name]=dict(pp=sha(pp.stdout),object=sha((out/(name+'.o')).read_bytes()))
    assert identities['baseline']==identities['absent']==identities['zero'],identities
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
    results=[]
    for shape in ('compact','limit','reuse'):
        mesh,side=b12.package(shape,3);groups,_=b12.metadata.build(mesh,side,2)
        data,_,_=b12.layout.convert(mesh,'direct-strips',side,groups)
        file=out/(shape+'.re4mesh');file.write_bytes(data)
        rows={}
        for arm in ('absent','on'):
            for case in range(21):
                p=run([binaries[arm],'route',case,file],env=env)
                (out/f'{shape}-{arm}-{case}.stdout').write_bytes(p.stdout)
                lines=p.stdout.splitlines();assert len(lines)==2
                rows[arm,case]=(json.loads(lines[0]),lines[1])
        # Full cache-free output on tight slabs equals the old generous route,
        # including every PVR header/vertex word, winding/UV/alpha and order.
        reference=rows['absent',13][1]
        for case in (0,2,3,4,14):
            row,words=rows['on',case]
            assert row['result']==1 and row['cache']==row['primed']==0 and row['commits']>0,(shape,case,row)
            assert words==reference,(shape,case,'tight direct output differs')
        for case in (5,6,7,8,9,10,11,12,13,15,16,17,18):
            assert rows['on',case][1]==rows['absent',case][1],(shape,case,'fallback/owner/rebind TA changed')
        assert rows['on',1][0]['result']<0 and not rows['on',1][0]['commits']
        assert rows['absent',0][0]['result']<0 and rows['absent',2][0]['result']<0
        for case in (19,20):
            assert rows['on',case][1]==rows['on',0][1],(shape,case,'failed continuation replayed or changed published prefix')
        results.append(dict(shape=shape,cases=21,observations=[dict(case=i,**rows['on',i][0]) for i in range(21)]))
    for path,digest in frozen.items():assert sha((ROOT/path).read_bytes())==digest,(path,'source changed during fixture')
    report=dict(status='PASS',base=BASE,scope=__doc__,sanitized=a.sanitize,off_host_identity=identities,
        boundaries=['current texture/SQ/SH4 arithmetic use the established hosted adapters',
            'generation publisher is an out-of-band fixture; actual mutation_current and bind consumer bodies execute',
            'immediate draw and queued full-pick consumers execute; no private incidence or target proof'],
        cases=results,source_sha256=frozen)
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='PASS',shapes=3,cases=63,off='host pp/object identity',sanitize=a.sanitize)))

if __name__=='__main__':main()
